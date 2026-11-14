"""Lazy access to the lightweight MOLA regional overview.

This service intentionally never initializes ``MarsPathfinder`` and never loads
the complete overview into memory.  It reads only the requested viewport from a
tiled, compressed GeoTIFF and caches a small number of recent response grids.
"""

from __future__ import annotations

from collections import OrderedDict
from threading import RLock
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform
from rasterio.windows import Window, from_bounds

from backend.config import (
    MOLA_SOURCE_COVERAGE,
    REGIONAL_BOUNDS,
    REGIONAL_FEATURES,
    REGIONAL_GRID_CACHE_SIZE,
    REGIONAL_GRID_MAX_RESOLUTION,
    REGIONAL_OVERVIEW_PATH,
    REGIONAL_PREVIEW_WEBP_PATH,
)


class RegionalTerrainService:
    """Read regional elevation windows without affecting Jezero analysis state."""

    _instance: "RegionalTerrainService | None" = None

    def __init__(self) -> None:
        self._cache: OrderedDict[tuple[float, float, float, float, int], dict[str, Any]] = OrderedDict()
        self._lock = RLock()

    @classmethod
    def get_instance(cls) -> "RegionalTerrainService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _clip_bounds(south: float, west: float, north: float, east: float) -> dict[str, float]:
        clipped = {
            "south": max(float(south), REGIONAL_BOUNDS["south"]),
            "west": max(float(west), REGIONAL_BOUNDS["west"]),
            "north": min(float(north), REGIONAL_BOUNDS["north"]),
            "east": min(float(east), REGIONAL_BOUNDS["east"]),
        }
        if clipped["south"] >= clipped["north"] or clipped["west"] >= clipped["east"]:
            raise ValueError("Requested viewport does not overlap the regional MOLA overview.")
        return clipped

    @staticmethod
    def _window(src: rasterio.DatasetReader, bounds: dict[str, float]) -> Window:
        geo = src.crs.geodetic_crs
        x, y = transform(
            geo,
            src.crs,
            [bounds["west"], bounds["east"], bounds["west"], bounds["east"]],
            [bounds["south"], bounds["south"], bounds["north"], bounds["north"]],
        )
        window = from_bounds(min(x), min(y), max(x), max(y), transform=src.transform)
        return window.round_offsets(op="floor").round_lengths(op="ceil").intersection(Window(0, 0, src.width, src.height))

    def metadata(self) -> dict[str, Any]:
        if not REGIONAL_OVERVIEW_PATH.is_file():
            return {
                "available": False,
                "message": "Regional overview has not been generated. Run: python backend/preprocess_mola.py --regional",
                "requested_bounds": REGIONAL_BOUNDS,
                "source_coverage": MOLA_SOURCE_COVERAGE,
            }
        with rasterio.open(REGIONAL_OVERVIEW_PATH) as src:
            return {
                "available": True,
                "dataset": "NASA MOLA MEGDR regional elevation overview",
                "requested_bounds": REGIONAL_BOUNDS,
                "source_coverage": MOLA_SOURCE_COVERAGE,
                "dimensions": {"width": src.width, "height": src.height},
                "compression": src.compression.value if src.compression else None,
                "tiled": bool(src.profile.get("tiled", False)),
                "overview_factors": src.overviews(1),
                "preview_url": "/static/regional_mola_overview.webp" if REGIONAL_PREVIEW_WEBP_PATH.is_file() else None,
                "geotiff_url": "/static/regional_mola_overview.tif",
                "analysis_scope": "Display-only regional overview; Jezero is the sole hazard, routing, and 3D analysis area.",
                "cache": {"strategy": "LRU viewport cache", "capacity": REGIONAL_GRID_CACHE_SIZE, "entries": len(self._cache)},
            }

    def features(self) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "properties": {"note": "Display extents are Gazetteer orientation aids, not analysis boundaries."},
            "features": [
                {
                    "type": "Feature",
                    "properties": {key: value for key, value in feature.items() if key != "bounds"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [feature["bounds"]["west"], feature["bounds"]["south"]],
                            [feature["bounds"]["east"], feature["bounds"]["south"]],
                            [feature["bounds"]["east"], feature["bounds"]["north"]],
                            [feature["bounds"]["west"], feature["bounds"]["north"]],
                            [feature["bounds"]["west"], feature["bounds"]["south"]],
                        ]],
                    },
                }
                for feature in REGIONAL_FEATURES
            ],
        }

    def grid(self, south: float, west: float, north: float, east: float, resolution: int = 256) -> dict[str, Any]:
        if not REGIONAL_OVERVIEW_PATH.is_file():
            raise FileNotFoundError("Regional overview is missing. Run: python backend/preprocess_mola.py --regional")
        bounds = self._clip_bounds(south, west, north, east)
        resolution = max(2, min(int(resolution), REGIONAL_GRID_MAX_RESOLUTION))
        key = (*[round(bounds[name], 5) for name in ("south", "west", "north", "east")], resolution)
        with self._lock:
            cached = self._cache.pop(key, None)
            if cached is not None:
                self._cache[key] = cached
                return {**cached, "cache": "hit"}

        with rasterio.open(REGIONAL_OVERVIEW_PATH) as src:
            window = self._window(src, bounds)
            width = min(resolution, max(2, int(window.width)))
            height = max(2, min(int(window.height), round(width * window.height / window.width)))
            masked = src.read(
                1,
                window=window,
                out_shape=(1, height, width),
                masked=True,
                resampling=Resampling.bilinear,
            )
            values = np.asarray(masked.filled(np.nan), dtype=np.float32).ravel()

        finite = values[np.isfinite(values)]
        response = {
            "bounds": bounds,
            "width": width,
            "height": height,
            "values": [round(float(v), 2) if np.isfinite(v) else None for v in values],
            "min": round(float(finite.min()), 2) if finite.size else None,
            "max": round(float(finite.max()), 2) if finite.size else None,
            "source": "NASA MOLA MEGDR local overview",
            "analysis_scope": "Display only; no regional hazards or pathfinding are calculated.",
        }
        with self._lock:
            self._cache[key] = response
            while len(self._cache) > REGIONAL_GRID_CACHE_SIZE:
                self._cache.popitem(last=False)
        return {**response, "cache": "miss"}
