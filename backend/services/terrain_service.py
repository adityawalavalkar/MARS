"""Terrain data and analysis caching service for Jezero Crater, Mars.

Maintains in-memory references to preprocessed MOLA rasters (elevation, slope,
hazard classifications, hazard scores) to provide sub-millisecond API response
times without re-reading rasters on every request.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import rasterio

from backend.config import (
    ELEVATION_RASTER_PATH,
    SLOPE_RASTER_PATH,
    HAZARD_CLASSES_RASTER_PATH,
    HAZARD_SCORE_RASTER_PATH,
    ELEVATION_MAP_PATH,
    SLOPE_MAP_PATH,
    SLOPE_CLASSES_MAP_PATH,
    HAZARD_MAP_PATH,
    HAZARD_OVERLAY_PATH,
    MARS_TERRAIN_MAP_PATH,
    TERRAIN_3D_HTML_PATH,
    TERRAIN_MESH_JSON_PATH,
    HAZARD_CLASSES,
    HAZARD_NODATA_VALUE,
    SLOPE_NODATA_VALUE,
    HAZARD_SCORE_NODATA_VALUE,
    SLOPE_GENTLE_MAX,
    SLOPE_MODERATE_MAX,
    OCTAVIA_E_BUTLER_LANDING_LAT,
    OCTAVIA_E_BUTLER_LANDING_LON,
)
from backend.analysis.pathfinding import MarsPathfinder
from backend.services.science_service import CRISMService, GeologyService


class TerrainService:
    """Central cached service providing terrain attributes, stats, and point queries."""

    _instance: Optional[TerrainService] = None

    def __init__(self):
        self.pathfinder = MarsPathfinder()
        self._cache_statistics()

    @classmethod
    def get_instance(cls) -> TerrainService:
        if cls._instance is None:
            cls._instance = TerrainService()
        return cls._instance

    def _cache_statistics(self) -> None:
        """Compute and cache summary statistics for rapid API delivery."""
        elev = self.pathfinder.elevation
        elev_nodata = self.pathfinder.elev_nodata
        valid_elev = elev != elev_nodata if elev_nodata is not None else np.ones_like(elev, dtype=bool)

        self.elev_min = float(np.min(elev[valid_elev]))
        self.elev_max = float(np.max(elev[valid_elev]))
        self.elev_mean = float(np.mean(elev[valid_elev]))
        self.elev_std = float(np.std(elev[valid_elev]))

        slope = self.pathfinder.slope
        valid_slope = slope[np.isfinite(slope) & (slope != SLOPE_NODATA_VALUE)]
        self.slope_min = float(np.min(valid_slope))
        self.slope_max = float(np.max(valid_slope))
        self.slope_mean = float(np.mean(valid_slope))
        self.slope_median = float(np.median(valid_slope))

        hazards = self.pathfinder.hazard_classes
        total_px = hazards.size
        safe_px = int(np.sum(hazards == 0))
        mod_px = int(np.sum(hazards == 1))
        high_px = int(np.sum(hazards == 2))
        nodata_px = int(np.sum(hazards == HAZARD_NODATA_VALUE))
        valid_px = total_px - nodata_px

        self.hazard_stats = {
            "total_pixels": total_px,
            "valid_pixels": valid_px,
            "safe_count": safe_px,
            "moderate_count": mod_px,
            "high_count": high_px,
            "nodata_count": nodata_px,
            "safe_pct": round(100.0 * safe_px / total_px, 2),
            "moderate_pct": round(100.0 * mod_px / total_px, 2),
            "high_pct": round(100.0 * high_px / total_px, 2),
            "nodata_pct": round(100.0 * nodata_px / total_px, 2),
            "valid_safe_pct": round(100.0 * safe_px / valid_px, 2) if valid_px else 0,
            "valid_moderate_pct": round(100.0 * mod_px / valid_px, 2) if valid_px else 0,
            "valid_high_pct": round(100.0 * high_px / valid_px, 2) if valid_px else 0,
        }

    def get_elevation_metadata(self) -> Dict[str, Any]:
        west, south, east, north = self.pathfinder.bounds_deg
        return {
            "dataset_name": "NASA MOLA MEGDR Jezero Elevation Product",
            "source_tile": "megt44n000hb.img",
            "dimensions": {"width": self.pathfinder.width, "height": self.pathfinder.height},
            "pixel_resolution_m": {
                "meridian_dy": round(self.pathfinder.dy, 2),
                "parallel_dx_min": round(float(np.min(self.pathfinder.dx_per_row)), 2),
                "parallel_dx_max": round(float(np.max(self.pathfinder.dx_per_row)), 2),
            },
            "bounds": {
                "west_deg": round(west, 5),
                "east_deg": round(east, 5),
                "south_deg": round(south, 5),
                "north_deg": round(north, 5),
            },
            "statistics": {
                "min_elevation_m": round(self.elev_min, 1),
                "max_elevation_m": round(self.elev_max, 1),
                "mean_elevation_m": round(self.elev_mean, 1),
                "std_elevation_m": round(self.elev_std, 1),
                "vertical_datum": "Mars Areoid (meters)",
            },
            "raster_file": "jezero_mola_elevation.tif",
            "visualization_file": "jezero_elevation_map.png",
        }

    def get_slope_metadata(self) -> Dict[str, Any]:
        return {
            "methodology": "Horn's 3x3 Gradient Operator on Equirectangular Metric Grid",
            "statistics": {
                "min_slope_deg": round(self.slope_min, 2),
                "max_slope_deg": round(self.slope_max, 2),
                "mean_slope_deg": round(self.slope_mean, 2),
                "median_slope_deg": round(self.slope_median, 2),
            },
            "thresholds": {
                "gentle_max_deg": SLOPE_GENTLE_MAX,
                "moderate_max_deg": SLOPE_MODERATE_MAX,
            },
            "distribution": {
                "gentle_count": int(np.sum((self.pathfinder.slope >= 0) & (self.pathfinder.slope <= 5.0))),
                "moderate_count": int(np.sum((self.pathfinder.slope > 5.0) & (self.pathfinder.slope <= 15.0))),
                "steep_count": int(np.sum(self.pathfinder.slope > 15.0)),
            },
            "raster_file": "jezero_slope.tif",
            "visualization_file": "jezero_slope_map.png",
            "classes_map_file": "jezero_slope_classes.png",
        }

    def get_hazard_metadata(self) -> Dict[str, Any]:
        return {
            "classification_scheme": HAZARD_CLASSES,
            "statistics": self.hazard_stats,
            "thresholds": {
                "slope_gentle_max_deg": SLOPE_GENTLE_MAX,
                "slope_moderate_max_deg": SLOPE_MODERATE_MAX,
                "class_2_policy": "Impassable by default (15°); requests may explicitly allow a higher slope up to the API limit.",
                "roughness_method": "Detrended 3x3 plane residual contributes to score only; class boundaries are slope-only.",
            },
            "disclaimer": (
                "Hazard classifications are project-defined mission engineering parameters. "
                "Not official NASA astronaut safety standards."
            ),
            "raster_file": "jezero_hazard_classes.tif",
            "score_raster_file": "jezero_hazard_score.tif",
            "visualization_file": "jezero_hazard_map.png",
            "overlay_file": "jezero_hazard_overlay.png",
            "mars_terrain_map_file": "jezero_mars_terrain_map.png",
        }

    def get_combined_statistics(self) -> Dict[str, Any]:
        west, south, east, north = self.pathfinder.bounds_deg
        return {
            "region": "Jezero Crater, Mars",
            "center": {"latitude_deg": 18.40625, "longitude_deg": 77.69531},
            "bounds": {"west": west, "east": east, "south": south, "north": north},
            "elevation": {
                "min_m": self.elev_min,
                "max_m": self.elev_max,
                "mean_m": self.elev_mean,
            },
            "slope": {
                "mean_deg": self.slope_mean,
                "max_deg": self.slope_max,
            },
            "hazards": self.hazard_stats,
        }

    def query_point(self, lon_deg: float, lat_deg: float) -> Dict[str, Any]:
        """Lookup physical and scientific attributes for a single planetary coordinate."""
        west, south, east, north = self.pathfinder.bounds_deg
        if not (west <= lon_deg <= east and south <= lat_deg <= north):
            return {
                "inside_study_area": False,
                "message": f"Coordinate ({lon_deg:.4f}°E, {lat_deg:.4f}°N) is outside the Jezero study area.",
            }

        r, c = self.pathfinder.coords_to_pixel(lon_deg, lat_deg)
        elev = float(self.pathfinder.elevation[r, c])
        slp = float(self.pathfinder.slope[r, c]) if np.isfinite(self.pathfinder.slope[r, c]) else None
        hz_cls = int(self.pathfinder.hazard_classes[r, c])
        hz_scr = float(self.pathfinder.hazard_score[r, c]) if self.pathfinder.hazard_score[r, c] >= 0 else None
        traversable = bool(self.pathfinder.is_traversable[r, c])

        class_info = HAZARD_CLASSES.get(hz_cls, HAZARD_CLASSES[HAZARD_NODATA_VALUE])
        geology = GeologyService.query_geology_at_coords(lon_deg, lat_deg)
        minerals = CRISMService.query_minerals_at_coords(lon_deg, lat_deg)

        return {
            "inside_study_area": True,
            "coordinates": {"longitude_deg": lon_deg, "latitude_deg": lat_deg},
            "raster_pixel": {"row": r, "col": c},
            "elevation_m": round(elev, 1),
            "slope_deg": round(slp, 2) if slp is not None else None,
            "hazard_class": hz_cls,
            "hazard_name": class_info["name"],
            "hazard_score": round(hz_scr, 3) if hz_scr is not None else None,
            "traversable": traversable,
            "geological_unit": geology,
            "detected_minerals": minerals,
        }

    def get_sample_routes(self) -> List[Dict[str, Any]]:
        """Return predefined scientifically curated sample routes across Jezero Crater."""
        return [
            {
                "id": "ROUTE_01",
                "name": "Octavia E. Butler Landing to Western Delta Front",
                "description": "Historical Perseverance rover traversal corridor towards the sedimentary fan.",
                "start": {"lon": OCTAVIA_E_BUTLER_LANDING_LON, "lat": OCTAVIA_E_BUTLER_LANDING_LAT},
                "destination": {"lon": 77.4580, "lat": 18.4180},
                "recommended_mode": "rover",
            },
            {
                "id": "ROUTE_02",
                "name": "Delta Scarp to Neretva Vallis Fluvial Inlet",
                "description": "Exploration of the ancient western lake inlet gorge.",
                "start": {"lon": 77.4180, "lat": 18.4580},
                "destination": {"lon": 77.3450, "lat": 18.5150},
                "recommended_mode": "crewed",
            },
            {
                "id": "ROUTE_03",
                "name": "Crater Floor Traverse to Séítah Olivine Dunes",
                "description": "Geological sampling run across the fractured igneous floor.",
                "start": {"lon": OCTAVIA_E_BUTLER_LANDING_LON, "lat": OCTAVIA_E_BUTLER_LANDING_LAT},
                "destination": {"lon": 77.4420, "lat": 18.4350},
                "recommended_mode": "rover",
            },
        ]
