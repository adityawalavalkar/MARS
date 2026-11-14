"""A* pathfinding and safe route planning engine for Mars surface traversal.

Calculates optimal candidate surface trajectories across Jezero Crater using
georeferenced MOLA elevation, slope gradient vectors, and hazard classification
costs. Supports customizable rover/astronaut mobility profiles, safety penalty
weights, and strict NoData avoidance.
"""

from __future__ import annotations

import heapq
import math
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct execution
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from typing import Any, Dict, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import rasterio
from rasterio.warp import transform

from backend.config import (
    ELEVATION_RASTER_PATH,
    SLOPE_RASTER_PATH,
    HAZARD_CLASSES_RASTER_PATH,
    HAZARD_SCORE_RASTER_PATH,
    SAMPLE_ROUTE_MAP_PATH,
    HAZARD_NODATA_VALUE,
    HAZARD_SCORE_NODATA_VALUE,
    MAX_TRAVERSABLE_SLOPE,
    SLOPE_NODATA_VALUE,
    MARS_RADIUS_M,
    DEFAULT_NOMINAL_SPEED_ROVER_KMH,
    DEFAULT_NOMINAL_SPEED_CREWED_KMH,
    DEFAULT_NOMINAL_SPEED_EVA_KMH,
)
from backend.utils.geo import (
    coords_to_pixel,
    pixel_to_coords,
    is_within_raster,
    euclidean_ground_distance,
)
from backend.utils.export import create_route_geojson


# 8-connected grid movement deltas (dr, dc)
NEIGHBOR_OFFSETS = [
    (-1, 0),  # North
    (1, 0),   # South
    (0, -1),  # West
    (0, 1),   # East
    (-1, -1), # North-West
    (-1, 1),  # North-East
    (1, -1),  # South-West
    (1, 1),   # South-East
]


class MarsPathfinder:
    """A* Pathfinding engine operating on Jezero Crater georeferenced raster products."""

    def __init__(
        self,
        elevation_path: Path = ELEVATION_RASTER_PATH,
        slope_path: Path = SLOPE_RASTER_PATH,
        hazard_classes_path: Path = HAZARD_CLASSES_RASTER_PATH,
        hazard_score_path: Path = HAZARD_SCORE_RASTER_PATH,
    ):
        self.elevation_path = elevation_path
        self.slope_path = slope_path
        self.hazard_classes_path = hazard_classes_path
        self.hazard_score_path = hazard_score_path

        self._load_rasters()

    def _load_rasters(self) -> None:
        """Load and cache raster datasets into numpy memory buffers."""
        with rasterio.open(self.elevation_path) as src:
            self.elevation = src.read(1)
            self.elev_nodata = src.nodata
            self.profile = src.profile.copy()
            self.crs = src.crs
            self.transform = src.transform
            self.height, self.width = src.height, src.width
            self.geo_crs = src.crs.geodetic_crs

            # Precalculate physical ground distance parameters
            params = self.crs.to_dict() if self.crs is not None else {}
            self.radius = float(params.get("R", params.get("a", MARS_RADIUS_M)))
            self.lat_ts = math.radians(float(params.get("lat_ts", 0.0)))
            self.lat_0 = math.radians(float(params.get("lat_0", 0.0)))
            self.y_0 = float(params.get("y_0", 0.0))

            rows = np.arange(self.height)
            northing = self.transform.f + self.transform.e * (rows + 0.5)
            self.row_latitudes = self.lat_0 + (northing - self.y_0) / self.radius
            self.dx_per_row = abs(self.transform.a) * np.cos(self.row_latitudes) / math.cos(self.lat_ts)
            self.dy = abs(self.transform.e)

            # Geographic outer extent
            left, top = self.transform.c, self.transform.f
            right = left + self.transform.a * self.width
            bottom = top + self.transform.e * self.height
            lons, lats = transform(self.crs, self.geo_crs, [left, right], [bottom, top])
            self.bounds_deg = (min(lons), min(lats), max(lons), max(lats))

        with rasterio.open(self.slope_path) as src:
            self.slope = src.read(1)

        with rasterio.open(self.hazard_classes_path) as src:
            self.hazard_classes = src.read(1)

        with rasterio.open(self.hazard_score_path) as src:
            self.hazard_score = src.read(1)

        # Precompute traversability boolean mask
        self.is_traversable = (
            (self.hazard_classes != HAZARD_NODATA_VALUE)
            & (self.hazard_score != HAZARD_SCORE_NODATA_VALUE)
            & np.isfinite(self.slope)
            & (self.slope != SLOPE_NODATA_VALUE)
        )
        if self.elev_nodata is not None:
            self.is_traversable &= (self.elevation != self.elev_nodata)

    def coords_to_pixel(self, lon_deg: float, lat_deg: float) -> Tuple[int, int]:
        """Convert planetary lon/lat degrees to raster row/col."""
        eastings, northings = transform(self.geo_crs, self.crs, [lon_deg], [lat_deg])
        r, c = rasterio.transform.rowcol(self.transform, eastings[0], northings[0])
        return int(r), int(c)

    def pixel_to_coords(self, row: int, col: int) -> Tuple[float, float]:
        """Convert raster row/col to planetary lon/lat degrees."""
        easting, northing = rasterio.transform.xy(self.transform, row, col)
        lons, lats = transform(self.crs, self.geo_crs, [easting], [northing])
        return float(lons[0]), float(lats[0])

    def find_nearest_traversable(self, row: int, col: int, max_radius: int = 5, max_slope_limit: float = MAX_TRAVERSABLE_SLOPE) -> Tuple[int, int]:
        """Search adjacent neighborhood for nearest traversable cell if target is blocked."""
        if self.is_traversable[row, col] and self.slope[row, col] <= max_slope_limit:
            return row, col

        best_cell = None
        min_dist = float("inf")
        for dr in range(-max_radius, max_radius + 1):
            for dc in range(-max_radius, max_radius + 1):
                nr, nc = row + dr, col + dc
                if (is_within_raster(nr, nc, self.height, self.width)
                        and self.is_traversable[nr, nc]
                        and self.slope[nr, nc] <= max_slope_limit):
                    d = math.hypot(dr, dc)
                    if d < min_dist:
                        min_dist = d
                        best_cell = (nr, nc)

        if best_cell is not None:
            return best_cell
        raise ValueError(f"No safe traversable cell within {max_radius} pixels of ({row}, {col}).")

    def plan_route(
        self,
        start_lon: float,
        start_lat: float,
        dest_lon: float,
        dest_lat: float,
        safety_weight: float = 1.5,
        max_slope_limit: float = MAX_TRAVERSABLE_SLOPE,
        mode: str = "rover",  # "rover", "crewed", or "eva"
    ) -> Dict[str, Any]:
        """Calculate optimal safe route using A* graph search on Mars terrain.

        Parameters:
        - start_lon, start_lat: Origin coordinates in planetary degrees
        - dest_lon, dest_lat: Destination coordinates in planetary degrees
        - safety_weight: Multiplier penalty for terrain hazards (1.0 = balanced, 3.0+ = high safety)
        - max_slope_limit: Maximum passable slope degrees before strictly impassable
        - mode: Mobility mode ('rover', 'crewed', or 'eva')

        Returns complete GeoJSON FeatureCollection, waypoint list, and mission metrics.
        """
        # Validate coordinates are within bounding box
        west, south, east, north = self.bounds_deg
        if not (west <= start_lon <= east and south <= start_lat <= north):
            raise ValueError(
                f"Start coordinate ({start_lon:.4f}°E, {start_lat:.4f}°N) is outside "
                f"study area ({west:.4f}–{east:.4f}°E, {south:.4f}–{north:.4f}°N)."
            )
        if not (west <= dest_lon <= east and south <= dest_lat <= north):
            raise ValueError(
                f"Destination coordinate ({dest_lon:.4f}°E, {dest_lat:.4f}°N) is outside "
                f"study area ({west:.4f}–{east:.4f}°E, {south:.4f}–{north:.4f}°N)."
            )

        start_r, start_c = self.coords_to_pixel(start_lon, start_lat)
        dest_r, dest_c = self.coords_to_pixel(dest_lon, dest_lat)

        # Check bounds in pixel space
        if not is_within_raster(start_r, start_c, self.height, self.width):
            raise ValueError(f"Start pixel ({start_r}, {start_c}) out of raster bounds.")
        if not is_within_raster(dest_r, dest_c, self.height, self.width):
            raise ValueError(f"Destination pixel ({dest_r}, {dest_c}) out of raster bounds.")

        # Find nearest traversable if on boundary/NoData
        start_r, start_c = self.find_nearest_traversable(start_r, start_c, max_slope_limit=max_slope_limit)
        dest_r, dest_c = self.find_nearest_traversable(dest_r, dest_c, max_slope_limit=max_slope_limit)

        if (start_r, start_c) == (dest_r, dest_c):
            lon, lat = self.pixel_to_coords(start_r, start_c)
            elev = float(self.elevation[start_r, start_c])
            slope = float(self.slope[start_r, start_c])
            hazard_class = int(self.hazard_classes[start_r, start_c])
            waypoint = [round(lon, 6), round(lat, 6), round(elev, 2)]
            summary = {
                "name": f"Jezero Candidate Route ({mode})", "mode": mode,
                "distance_km": 0.0, "total_distance_m": 0.0,
                "duration_hours": 0.0, "duration_sols": 0.0,
                "waypoints_count": 1, "avg_slope_deg": round(slope, 2),
                "max_slope_deg": round(slope, 2), "elevation_min_m": round(elev, 1),
                "elevation_max_m": round(elev, 1), "elevation_gain_m": 0.0,
                "elevation_loss_m": 0.0, "difficulty_score": 0.0,
                "feasibility": "GO", "feasibility_note": "Zero-length route; no traverse exposure.",
                "safety_weight": safety_weight,
                "hazard_exposure": {"safe_pct": 100.0 if hazard_class == 0 else 0.0,
                                    "moderate_pct": 100.0 if hazard_class == 1 else 0.0,
                                    "high_pct": 100.0 if hazard_class == 2 else 0.0},
                "disclaimer": "Candidate model route; not an official NASA astronaut-certified path.",
            }
            details = [{"step": 0, "row": start_r, "col": start_c,
                        "longitude_deg": round(lon, 6), "latitude_deg": round(lat, 6),
                        "elevation_m": round(elev, 2), "slope_deg": round(slope, 2),
                        "hazard_class": hazard_class,
                        "hazard_score": round(float(self.hazard_score[start_r, start_c]), 3),
                        "cumulative_dist_m": 0.0}]
            return {
                "success": True,
                "message": "Start and destination coincide.",
                "summary": summary,
                "waypoints": [waypoint],
                "path_details": details,
                "geojson": create_route_geojson([waypoint, waypoint], summary),
            }

        # A* Search Priority Queue: (f_score, current_row, current_col)
        open_set: List[Tuple[float, int, int]] = []
        heapq.heappush(open_set, (0.0, start_r, start_c))

        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score = np.full((self.height, self.width), np.inf, dtype=np.float64)
        g_score[start_r, start_c] = 0.0

        f_score = np.full((self.height, self.width), np.inf, dtype=np.float64)
        h_start = euclidean_ground_distance(start_r, start_c, dest_r, dest_c, self.dx_per_row, self.dy)
        f_score[start_r, start_c] = h_start

        visited = np.zeros((self.height, self.width), dtype=bool)

        dest_reached = False

        while open_set:
            current_f, cur_r, cur_c = heapq.heappop(open_set)

            if visited[cur_r, cur_c]:
                continue
            visited[cur_r, cur_c] = True

            if (cur_r, cur_c) == (dest_r, dest_c):
                dest_reached = True
                break

            current_z = float(self.elevation[cur_r, cur_c])

            for dr, dc in NEIGHBOR_OFFSETS:
                nr, nc = cur_r + dr, cur_c + dc

                if not is_within_raster(nr, nc, self.height, self.width):
                    continue
                if visited[nr, nc] or not self.is_traversable[nr, nc]:
                    continue

                cell_slope = float(self.slope[nr, nc])
                if cell_slope > max_slope_limit:
                    continue

                # Ground distance between pixel centers in meters
                step_dist = euclidean_ground_distance(cur_r, cur_c, nr, nc, self.dx_per_row, self.dy)
                next_z = float(self.elevation[nr, nc])
                dz = next_z - current_z
                climb_slope_deg = math.degrees(math.atan2(abs(dz), step_dist))

                if climb_slope_deg > max_slope_limit:
                    continue

                # Cost Calculation
                # Slope penalty: squared penalty for slopes above 5°
                slope_penalty = 2.5 * ((max(0.0, cell_slope) / 10.0) ** 2)

                # Hazard score penalty (0.0 to 1.0)
                h_val = float(self.hazard_score[nr, nc])
                hazard_penalty = safety_weight * 6.0 * (h_val ** 2)

                # Step traversal cost
                traversal_cost = step_dist * (1.0 + slope_penalty + hazard_penalty)

                tentative_g = g_score[cur_r, cur_c] + traversal_cost

                if tentative_g < g_score[nr, nc]:
                    came_from[(nr, nc)] = (cur_r, cur_c)
                    g_score[nr, nc] = tentative_g

                    # Admissible heuristic: Euclidean ground distance
                    h = euclidean_ground_distance(nr, nc, dest_r, dest_c, self.dx_per_row, self.dy)
                    f_score[nr, nc] = tentative_g + h
                    heapq.heappush(open_set, (f_score[nr, nc], nr, nc))

        if not dest_reached:
            raise RuntimeError(
                f"No traversable route found between ({start_lon:.4f}, {start_lat:.4f}) and "
                f"({dest_lon:.4f}, {dest_lat:.4f}) within slope limit of {max_slope_limit}°."
            )

        # Reconstruct path
        path_pixels: List[Tuple[int, int]] = []
        curr = (dest_r, dest_c)
        while curr in came_from:
            path_pixels.append(curr)
            curr = came_from[curr]
        path_pixels.append((start_r, start_c))
        path_pixels.reverse()

        # Build trajectory profile and waypoints
        waypoints: List[List[float]] = []
        path_details: List[Dict[str, Any]] = []

        cumulative_dist_m = 0.0
        elevations: List[float] = []
        slopes: List[float] = []
        hazard_classes_list: List[int] = []
        elevation_gain_m = 0.0
        elevation_loss_m = 0.0

        # Mobility nominal speeds
        if mode == "crewed":
            v_nom_kmh = DEFAULT_NOMINAL_SPEED_CREWED_KMH
        elif mode == "eva":
            v_nom_kmh = DEFAULT_NOMINAL_SPEED_EVA_KMH
        else:
            v_nom_kmh = DEFAULT_NOMINAL_SPEED_ROVER_KMH

        total_duration_hours = 0.0

        for idx, (pr, pc) in enumerate(path_pixels):
            lon, lat = self.pixel_to_coords(pr, pc)
            elev = float(self.elevation[pr, pc])
            slp = float(self.slope[pr, pc])
            hz_cls = int(self.hazard_classes[pr, pc])
            hz_scr = float(self.hazard_score[pr, pc])

            elevations.append(elev)
            slopes.append(slp)
            hazard_classes_list.append(hz_cls)

            step_ground_m = 0.0
            if idx > 0:
                prev_r, prev_c = path_pixels[idx - 1]
                step_ground_m = euclidean_ground_distance(prev_r, prev_c, pr, pc, self.dx_per_row, self.dy)
                cumulative_dist_m += step_ground_m

                prev_z = elevations[-2]
                delta_z = elev - prev_z
                if delta_z > 0:
                    elevation_gain_m += delta_z
                else:
                    elevation_loss_m += abs(delta_z)

                # Tobler speed on Mars (km/h): adjusted for slope
                step_grade = delta_z / step_ground_m if step_ground_m > 0 else 0.0
                speed_factor = math.exp(-3.5 * abs(step_grade + 0.05))
                eff_speed_kmh = max(0.02, v_nom_kmh * speed_factor)
                step_time_h = (step_ground_m / 1000.0) / eff_speed_kmh
                total_duration_hours += step_time_h

            waypoints.append([round(lon, 6), round(lat, 6), round(elev, 2)])
            path_details.append({
                "step": idx,
                "row": pr,
                "col": pc,
                "longitude_deg": round(lon, 6),
                "latitude_deg": round(lat, 6),
                "elevation_m": round(elev, 2),
                "slope_deg": round(slp, 2),
                "hazard_class": hz_cls,
                "hazard_score": round(hz_scr, 3),
                "cumulative_dist_m": round(cumulative_dist_m, 2),
            })

        total_dist_km = cumulative_dist_m / 1000.0

        # Hazard exposure percentages
        n_steps = len(hazard_classes_list)
        safe_steps = sum(1 for c in hazard_classes_list if c == 0)
        mod_steps = sum(1 for c in hazard_classes_list if c == 1)
        high_steps = sum(1 for c in hazard_classes_list if c == 2)

        # Route difficulty index: normalized 0.0 to 10.0
        avg_slope = float(np.mean(slopes)) if slopes else 0.0
        max_slope = float(np.max(slopes)) if slopes else 0.0
        difficulty_score = min(10.0, round((avg_slope / 3.0) + (max_slope / 6.0) + (high_steps / n_steps * 5.0), 2))

        # Feasibility assessment
        if max_slope > 18.0 or (high_steps / n_steps) > 0.15:
            feasibility = "CAUTION"
            feasibility_note = "Route encounters significant slopes > 15°. Enhanced traction required."
        else:
            feasibility = "GO"
            feasibility_note = "Route traverses nominal, low-to-moderate hazard terrain within safety tolerances."

        properties = {
            "name": f"Jezero Candidate Route ({mode})",
            "mode": mode,
            "distance_km": round(total_dist_km, 3),
            "total_distance_m": round(cumulative_dist_m, 1),
            "duration_hours": round(total_duration_hours, 2),
            "duration_sols": round(total_duration_hours / 24.66, 3),
            "waypoints_count": len(waypoints),
            "avg_slope_deg": round(avg_slope, 2),
            "max_slope_deg": round(max_slope, 2),
            "elevation_min_m": round(float(np.min(elevations)), 1),
            "elevation_max_m": round(float(np.max(elevations)), 1),
            "elevation_gain_m": round(elevation_gain_m, 1),
            "elevation_loss_m": round(elevation_loss_m, 1),
            "difficulty_score": difficulty_score,
            "feasibility": feasibility,
            "feasibility_note": feasibility_note,
            "safety_weight": safety_weight,
            "hazard_exposure": {
                "safe_pct": round(100.0 * safe_steps / n_steps, 1),
                "moderate_pct": round(100.0 * mod_steps / n_steps, 1),
                "high_pct": round(100.0 * high_steps / n_steps, 1),
            },
            "disclaimer": (
                "Candidate model route generated via A* geospatial cost function. "
                "Not an official NASA astronaut-certified path."
            ),
        }

        geojson = create_route_geojson(waypoints, properties)

        return {
            "success": True,
            "summary": properties,
            "waypoints": waypoints,
            "path_details": path_details,
            "geojson": geojson,
        }


def render_sample_route_map(
    pathfinder: MarsPathfinder,
    route_result: Dict[str, Any],
    output_path: Path = SAMPLE_ROUTE_MAP_PATH,
) -> None:
    """Render professional dual-panel cartographic figure showing map and elevation profile."""
    waypoints = route_result["waypoints"]
    summary = route_result["summary"]

    lons = [w[0] for w in waypoints]
    lats = [w[1] for w in waypoints]
    elevs = [w[2] for w in waypoints]
    dists_km = [d["cumulative_dist_m"] / 1000.0 for d in route_result["path_details"]]

    # Read base elevation for background
    with rasterio.open(pathfinder.elevation_path) as src:
        elevation = src.read(1)
        west, south, east, north = pathfinder.bounds_deg
        mean_lat = (south + north) / 2.0
        aspect = 1.0 / math.cos(math.radians(mean_lat))

    from backend.analysis.realistic_map import create_mars_colormap, compute_hillshade
    hillshade = compute_hillshade(elevation, pathfinder.dx_per_row[128], pathfinder.dy, z_factor=2.5)
    mars_cmap = create_mars_colormap()

    min_elev, max_elev = float(np.min(elevation)), float(np.max(elevation))
    norm_elev = np.clip((elevation - min_elev) / (max_elev - min_elev), 0.0, 1.0)
    rgb_elev = mars_cmap(norm_elev)[:, :, :3]
    rgb_terrain = np.clip(rgb_elev * (0.35 + 0.65 * hillshade[:, :, np.newaxis]), 0.0, 1.0)

    # Figure with 2 subplots: Map on top, Profile on bottom
    fig, (ax_map, ax_prof) = plt.subplots(
        2, 1, figsize=(10, 11), gridspec_kw={"height_ratios": [3.2, 1.0]}, dpi=200, facecolor="#0e0e12"
    )
    for ax in (ax_map, ax_prof):
        ax.set_facecolor("#0e0e12")
        for spine in ax.spines.values():
            spine.set_color("#555566")

    # Panel 1: Map
    ax_map.imshow(rgb_terrain, extent=(west, east, south, north), origin="upper", interpolation="bilinear")
    ax_map.set_aspect(aspect)
    ax_map.set_title(
        f"MARS-NAV: Safe Candidate Route Plan — {summary['name']}",
        fontsize=13,
        fontweight="bold",
        color="#ffffff",
        pad=12,
    )
    ax_map.set_xlabel("Longitude (°E)", color="#d0d0d8", fontsize=10)
    ax_map.set_ylabel("Latitude (°N)", color="#d0d0d8", fontsize=10)
    ax_map.tick_params(colors="#d0d0d8", labelsize=9)
    ax_map.grid(color="#ffffff", alpha=0.15, linestyle="--")

    # Plot Route Line
    ax_map.plot(lons, lats, color="#00ffcc", linewidth=3.0, label=f"Candidate Path ({summary['distance_km']} km)", zorder=4)

    # Plot Start and Dest
    ax_map.plot(lons[0], lats[0], marker="o", color="#00ff00", markersize=10, markeredgecolor="black", label="Start Point", zorder=5)
    ax_map.plot(lons[-1], lats[-1], marker="X", color="#ff0055", markersize=12, markeredgecolor="white", label="Destination Point", zorder=5)

    ax_map.legend(loc="upper right", facecolor="#14141c", edgecolor="#444455", labelcolor="#ffffff", fontsize=9)

    # Panel 2: Elevation Profile
    ax_prof.plot(dists_km, elevs, color="#00ffcc", linewidth=2.0)
    ax_prof.fill_between(dists_km, elevs, min(elevs) - 50, color="#00ffcc", alpha=0.2)
    ax_prof.set_title("Route Topographic Elevation Profile", color="#ffffff", fontsize=11, fontweight="bold")
    ax_prof.set_xlabel("Traverse Distance (km)", color="#d0d0d8", fontsize=10)
    ax_prof.set_ylabel("Elevation (m)", color="#d0d0d8", fontsize=10)
    ax_prof.tick_params(colors="#d0d0d8", labelsize=9)
    ax_prof.grid(color="#ffffff", alpha=0.15, linestyle="--")

    # Statistics text
    ax_prof.text(
        0.02,
        0.80,
        f"Est. Duration: {summary['duration_hours']} hrs | Avg Slope: {summary['avg_slope_deg']}° | "
        f"Max Slope: {summary['max_slope_deg']}° | Feasibility: {summary['feasibility']}",
        transform=ax_prof.transAxes,
        color="#ffffff",
        fontsize=9,
        bbox={"facecolor": "#181822", "alpha": 0.85, "edgecolor": "#555566", "pad": 3},
    )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)


def run_sample_route_test() -> Dict[str, Any]:
    """Test pathfinding engine on representative Jezero Crater traverse routes."""
    finder = MarsPathfinder()

    # Route: From Perseverance landing site eastward into Jezero crater floor
    start_lon, start_lat = 77.4508, 18.4447  # Octavia E. Butler Landing Site
    dest_lon, dest_lat = 77.6200, 18.4100    # Crater Floor Science Target

    print(f"Planning candidate route from ({start_lon}, {start_lat}) to ({dest_lon}, {dest_lat})...")
    result = finder.plan_route(start_lon, start_lat, dest_lon, dest_lat, safety_weight=1.5, mode="rover")

    print("Path planning succeeded!")
    print(f"  Distance: {result['summary']['distance_km']} km")
    print(f"  Duration: {result['summary']['duration_hours']} hours ({result['summary']['duration_sols']} sols)")
    print(f"  Avg Slope: {result['summary']['avg_slope_deg']}°, Max Slope: {result['summary']['max_slope_deg']}°")
    print(f"  Difficulty: {result['summary']['difficulty_score']} / 10.0")
    print(f"  Feasibility: {result['summary']['feasibility']}")

    # Render route map
    print("Rendering sample route map...")
    render_sample_route_map(finder, result)
    print(f"Route map saved to: {SAMPLE_ROUTE_MAP_PATH}")

    return result


if __name__ == "__main__":
    run_sample_route_test()
