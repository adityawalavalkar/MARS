"""Dashboard-facing adapters built on the MARS-NAV domain services.

The React dashboard was developed against compact, map-friendly payloads.  This
router exposes those payloads while delegating every calculation to the existing
terrain, routing, mission, and science services.  The original public API routes
remain unchanged.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.ndimage import map_coordinates
from rasterio.warp import transform as warp_transform
from fastapi import APIRouter, HTTPException, Query

from backend.analysis.mission import calculate_mission_analysis
from backend.services.science_service import CRISMService, MarsClimateService, RadiationService
from backend.services.terrain_service import TerrainService
from backend.utils.geo import great_circle_distance_mars


router = APIRouter(prefix="/api", tags=["Dashboard Integration"])


def _bounds(service: TerrainService, south: float, west: float, north: float, east: float) -> tuple[int, int, int, int, dict[str, float]]:
    """Clip a requested geographic window to the cached MOLA raster."""
    raster_west, raster_south, raster_east, raster_north = service.pathfinder.bounds_deg
    west, east = max(west, raster_west), min(east, raster_east)
    south, north = max(south, raster_south), min(north, raster_north)
    if west >= east or south >= north:
        raise HTTPException(status_code=422, detail="Requested bounds do not overlap the Jezero study area.")
    top, left = service.pathfinder.coords_to_pixel(west, north)
    bottom, right = service.pathfinder.coords_to_pixel(east, south)
    row0, row1 = sorted((top, bottom))
    col0, col1 = sorted((left, right))
    row1, col1 = min(row1 + 1, service.pathfinder.height), min(col1 + 1, service.pathfinder.width)
    return row0, row1, col0, col1, {"south": south, "west": west, "north": north, "east": east}


def _resample(values: np.ndarray, width: int, height: int, invalid: set[float] | None = None, order: int = 1) -> list[float | None]:
    """Bilinear continuous grids; categorical hazard classes request nearest explicitly."""
    rows = np.linspace(0, values.shape[0] - 1, height)
    cols = np.linspace(0, values.shape[1] - 1, width)
    rr, cc = np.meshgrid(rows, cols, indexing="ij")
    sampled = map_coordinates(values.astype(np.float64), [rr, cc], order=order, mode="nearest").ravel()
    invalid = invalid or set()
    return [None if not math.isfinite(v) or v in invalid else round(float(v), 4) for v in sampled]


def _grid(values: np.ndarray, bounds: dict[str, float], resolution: int, invalid: set[float] | None = None, order: int = 1) -> dict[str, Any]:
    size = max(2, min(int(resolution), 256))
    output = _resample(values, size, size, invalid, order=order)
    valid = [v for v in output if v is not None]
    return {
        "width": size,
        "height": size,
        "values": output,
        "min": min(valid) if valid else None,
        "max": max(valid) if valid else None,
        "bounds": bounds,
    }


@router.get("/weather", summary="Dashboard weather conditions")
def dashboard_weather(
    sol_time_hours: float = Query(..., ge=0.0, le=24.66),
    solar_longitude_ls: float = Query(..., ge=0.0, le=360.0),
    longitude_deg: float = Query(77.4508, ge=-180.0, le=360.0),
    region_id: str = Query("jezero", alias="regionId"),
):
    if region_id != "jezero":
        raise HTTPException(status_code=422, detail="Modeled weather estimate is Jezero-only.")
    prediction = MarsClimateService.predict_current_environment(sol_time_hours, solar_longitude_ls)
    return {
        "temperatureC": prediction["ambient_temperature_celsius"],
        "windSpeedKmh": round(prediction["estimated_wind_speed_ms"] * 3.6, 1),
        "localSolarTimeHours": sol_time_hours,
        "solarLongitudeLs": solar_longitude_ls,
        "longitudeDeg": longitude_deg,
        "source": "Modeled estimate (MEDA-based), Jezero-only",
    }


@router.get("/dashboard/radiation", summary="Dashboard radiation conditions")
def dashboard_radiation(mission_hours: float = Query(24.0, ge=0.1, le=8760.0), region_id: str = Query("jezero", alias="regionId")):
    if region_id != "jezero":
        raise HTTPException(status_code=422, detail="Radiation is a Gale-to-Jezero transfer estimate; it is available for Jezero only.")
    profile = RadiationService.get_radiation_profile()
    # The service reports mSv/h; the UI displays the equivalent µSv/h.
    return {
        "doseRateUSvH": round(profile["surface_equivalent_dose_rate_msv_per_hour"] * 1000, 3),
        "source": "Modeled Gale-to-Jezero transfer estimate (MSL RAD based), Jezero-only",
        "missionHours": mission_hours,
    }


@router.get("/hazard-grid", summary="Dashboard hazard score grid")
def dashboard_hazard_grid(
    south: float, west: float, north: float, east: float, resolution: int = Query(128, ge=2, le=256)
):
    service = TerrainService.get_instance()
    r0, r1, c0, c1, clipped = _bounds(service, south, west, north, east)
    payload = _grid(service.pathfinder.hazard_score[r0:r1, c0:c1], clipped, resolution, {-9999.0}, order=1)
    valid = [v for v in payload["values"] if v is not None]
    score = sum(valid) / len(valid) if valid else None
    payload["summary"] = {
        "score": round(score, 4) if score is not None else None,
        "level": "Low" if score is not None and score < 0.34 else "Medium" if score is not None and score < 0.67 else "High",
        "confidence": round(len(valid) / len(payload["values"]), 4),
    }
    return payload


@router.get("/elevation-grid", summary="Dashboard elevation and slope grids")
def dashboard_elevation_grid(
    south: float, west: float, north: float, east: float, resolution: int = Query(128, ge=2, le=256)
):
    service = TerrainService.get_instance()
    r0, r1, c0, c1, clipped = _bounds(service, south, west, north, east)
    payload = _grid(service.pathfinder.elevation[r0:r1, c0:c1], clipped, resolution, {service.pathfinder.elev_nodata}, order=1)
    slope = _grid(service.pathfinder.slope[r0:r1, c0:c1], clipped, resolution, {-9999.0}, order=1)
    payload["slope"] = slope["values"]
    payload["features"] = [
        {"label": "Perseverance landing site", "lat": 18.4447, "lon": 77.4508, "approximate": True},
        {"label": "Séítah (approximate center)", "lat": 18.4350, "lon": 77.4420, "approximate": True},
        {"label": "Neretva Vallis inlet (approximate)", "lat": 18.5200, "lon": 77.3400, "approximate": True},
        {"label": "Western delta (approximate)", "lat": 18.4650, "lon": 77.4000, "approximate": True},
    ]
    return payload


@router.get("/composition", summary="Dashboard CRISM detection catalog")
def dashboard_composition():
    minerals = CRISMService.get_all_minerals()
    # CRISM provides detections, not areal abundance.  Equal visual weights are
    # deliberately avoided; UI consumers receive the authoritative confidence.
    return {"components": [{"name": item["name"], "confidence": item["confidence"]} for item in minerals], "basis": "CRISM detection catalog; not mineral abundance"}


@router.get("/mineral-ratio", summary="Dashboard CRISM detection catalog")
def dashboard_mineral_ratio():
    minerals = CRISMService.get_all_minerals()
    return {"ratio": None, "minerals": [{"name": item["name"], "confidence": item["confidence"]} for item in minerals], "basis": "No mineral abundance ratio is available from the curated CRISM catalog."}


@router.post("/route", summary="Plan a dashboard route")
def dashboard_route(payload: dict[str, Any]):
    start, end = payload.get("start"), payload.get("end")
    if not isinstance(start, dict) or not isinstance(end, dict):
        raise HTTPException(status_code=422, detail="Route requires start and end {lat, lon} coordinates.")
    mode = payload.get("mode", "rover")
    safety_weight = float(payload.get("safety_weight", 1.5))
    max_slope_limit = float(payload.get("max_slope_limit", 15.0))
    crew_size = int(payload.get("crew_size", 2))
    if mode not in {"rover", "crewed", "eva"}:
        raise HTTPException(status_code=422, detail="mode must be rover, crewed, or eva.")
    if not 0.0 <= safety_weight <= 10.0:
        raise HTTPException(status_code=422, detail="safety_weight must be between 0 and 10.")
    if not 5.0 <= max_slope_limit <= 45.0:
        raise HTTPException(status_code=422, detail="max_slope_limit must be between 5 and 45 degrees.")
    if not 1 <= crew_size <= 6:
        raise HTTPException(status_code=422, detail="crew_size must be between 1 and 6.")
    try:
        service = TerrainService.get_instance()
        planner = service.pathfinder.plan_route
        route_args = dict(
            start_lon=float(start["lon"]), start_lat=float(start["lat"]),
            dest_lon=float(end["lon"]), dest_lat=float(end["lat"]),
            mode=mode, max_slope_limit=max_slope_limit,
        )
        result = planner(**route_args, safety_weight=safety_weight)
        analysis = calculate_mission_analysis(result, crew_size=crew_size)
        comparisons = []
        for label, weight in (("Fast", 0.5), ("Safe", 3.0)):
            candidate = planner(**route_args, safety_weight=weight)
            candidate_line = next(f for f in candidate["geojson"]["features"] if f.get("geometry", {}).get("type") == "LineString")
            comparisons.append({"label": label, "safetyWeight": weight, "feature": candidate_line})
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    line = next((f for f in result["geojson"]["features"] if f.get("geometry", {}).get("type") == "LineString"), None)
    if line is None:
        raise HTTPException(status_code=500, detail="Route planner returned no line geometry.")
    summary = result["summary"]
    line["properties"] = {
        **line.get("properties", {}),
        "distanceKm": summary["distance_km"],
        "durationHours": summary["duration_hours"],
        "difficultyScore": summary["difficulty_score"],
        "feasibility": summary["feasibility"],
        "hazardExposure": summary["hazard_exposure"],
        "safetyWeight": safety_weight,
        "mode": mode,
        "energy": analysis.get("energy_requirements", {}),
        "evaDurationCheck": next((item for item in analysis.get("feasibility_checks", []) if item.get("parameter") == "EVA Duration Limit"), None),
        "crewSize": crew_size,
        "comparison": comparisons,
        "waypoints": [{"lon": point[0], "lat": point[1]} for point in result["waypoints"]],
        "missionAnalysis": analysis,
    }
    return line


@router.post("/elevation-profile", summary="Extract elevation profile from a planned route")
def dashboard_elevation_profile(payload: dict[str, Any]):
    coords = payload.get("route", {}).get("geometry", {}).get("coordinates", [])
    if not isinstance(coords, list) or len(coords) < 2:
        raise HTTPException(status_code=422, detail="A LineString route with at least two coordinates is required.")
    service = TerrainService.get_instance()
    vertices: list[tuple[float, float]] = []
    for point in coords:
        if not isinstance(point, list) or len(point) < 2:
            raise HTTPException(status_code=422, detail="Invalid route coordinate.")
        lon, lat = float(point[0]), float(point[1])
        vertices.append((lon, lat))

    segment_km = [great_circle_distance_mars(a[0], a[1], b[0], b[1]) / 1000.0 for a, b in zip(vertices, vertices[1:])]
    cumulative = np.concatenate(([0.0], np.cumsum(segment_km)))
    total_km = float(cumulative[-1])
    interval_km = 0.4630576672  # Native MOLA raster pixel spacing, 463.06 m.
    distances = np.arange(0.0, total_km, interval_km).tolist()
    if not distances or total_km - distances[-1] > 1e-6:
        distances.append(total_km)
    else:
        distances[-1] = total_km

    sample_lons: list[float] = []
    sample_lats: list[float] = []
    for distance in distances:
        index = min(int(np.searchsorted(cumulative, distance, side="right") - 1), len(vertices) - 2)
        width = cumulative[index + 1] - cumulative[index]
        fraction = (distance - cumulative[index]) / width if width > 0 else 0.0
        sample_lons.append(vertices[index][0] + (vertices[index + 1][0] - vertices[index][0]) * fraction)
        sample_lats.append(vertices[index][1] + (vertices[index + 1][1] - vertices[index][1]) * fraction)

    finder = service.pathfinder
    xs, ys = warp_transform(finder.geo_crs, finder.crs, sample_lons, sample_lats)
    inverse_transform = ~finder.transform
    pixel_coords = [inverse_transform @ (x, y) for x, y in zip(xs, ys)]
    rows = np.asarray([p[1] - 0.5 for p in pixel_coords])
    cols = np.asarray([p[0] - 0.5 for p in pixel_coords])
    elevations = map_coordinates(finder.elevation.astype(np.float64), [rows, cols], order=1, mode="nearest").tolist()
    return {
        "distancesKm": [round(float(d), 4) for d in distances],
        "elevations": [round(float(z), 2) for z in elevations],
        "sampleIntervalKm": interval_km,
        "min": round(float(np.min(elevations)), 2),
        "max": round(float(np.max(elevations)), 2),
    }


@router.post("/mission-report", summary="Return mission report for a dashboard route")
def dashboard_mission_report(payload: dict[str, Any]):
    props = payload.get("route", {}).get("properties", {})
    analysis = props.get("missionAnalysis")
    if not isinstance(analysis, dict):
        raise HTTPException(status_code=422, detail="Plan a route before requesting its mission report.")
    energy = analysis.get("energy_requirements", {})
    consumables = analysis.get("life_support_consumables", {})
    return {
        "distanceKm": props.get("distanceKm"),
        "travelTimeHours": props.get("durationHours"),
        "difficultyScore": props.get("difficultyScore"),
        "feasibility": props.get("feasibility"),
        "hazardExposure": props.get("hazardExposure"),
        "mode": props.get("mode"),
        "evaDurationCheck": props.get("evaDurationCheck"),
        "resources": {
            "powerKwh": energy.get("total_energy_kwh"),
            "propulsionKwh": energy.get("propulsion_energy_kwh"),
            "hotelKwh": energy.get("hotel_load_energy_kwh"),
            "fuelKg": None,
            "waterL": consumables.get("estimated_total_water_liters"),
            "oxygenKg": consumables.get("estimated_oxygen_consumed_kg"),
        },
        "summary": analysis.get("summary_verdict", ""),
        "generatedAt": None,
    }
