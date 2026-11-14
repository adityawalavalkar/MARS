"""Terrain, slope, hazard assessment, and 3D visualization API endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.config import (
    TERRAIN_3D_HTML_PATH,
    TERRAIN_MESH_JSON_PATH,
    ELEVATION_RASTER_PATH,
    SLOPE_RASTER_PATH,
    HAZARD_CLASSES_RASTER_PATH,
)
from backend.services.terrain_service import TerrainService
from backend.services.regional_terrain_service import RegionalTerrainService
from backend.models.schemas import (
    HealthResponse,
    TerrainElevationResponse,
    TerrainSlopeResponse,
    TerrainHazardsResponse,
    TerrainStatsResponse,
    PointQueryResponse,
)

router = APIRouter(prefix="/api/terrain", tags=["Terrain & Hazards"])


@router.get("/regional", summary="Get Regional MOLA Overview Metadata")
async def get_regional_overview():
    """Return lightweight regional dataset metadata without loading Jezero analysis rasters."""
    return RegionalTerrainService.get_instance().metadata()


@router.get("/regional/features", summary="Get Regional Gazetteer Display Features")
async def get_regional_features():
    """Return labelled regional feature extents for map orientation only."""
    return RegionalTerrainService.get_instance().features()


@router.get("/regional/grid", summary="Read a Lazy-Loaded Regional MOLA Viewport")
async def get_regional_grid(
    south: float = Query(..., ge=-90.0, le=90.0),
    west: float = Query(..., ge=-180.0, le=360.0),
    north: float = Query(..., ge=-90.0, le=90.0),
    east: float = Query(..., ge=-180.0, le=360.0),
    resolution: int = Query(256, ge=2, le=512),
):
    """Read and resample only the current regional map viewport, using the LRU cache."""
    try:
        return RegionalTerrainService.get_instance().grid(south, west, north, east, resolution)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/elevation", response_model=TerrainElevationResponse, summary="Get MOLA Elevation Metadata & Stats")
async def get_elevation_info():
    """Retrieve Jezero Crater elevation dataset parameters, bounding box, and vertical range."""
    service = TerrainService.get_instance()
    return service.get_elevation_metadata()


@router.get("/slope", response_model=TerrainSlopeResponse, summary="Get Horn 3x3 Slope Analysis")
async def get_slope_info():
    """Retrieve Jezero slope gradient statistics, bins (gentle, moderate, steep), and raster metadata."""
    service = TerrainService.get_instance()
    return service.get_slope_metadata()


@router.get("/hazards", response_model=TerrainHazardsResponse, summary="Get Terrain Hazard Assessment")
async def get_hazards_info():
    """Retrieve classified terrain hazard distributions, engineering thresholds, and map paths."""
    service = TerrainService.get_instance()
    return service.get_hazard_metadata()


@router.get("/statistics", response_model=TerrainStatsResponse, summary="Get Comprehensive Terrain Summary")
async def get_statistics():
    """Combined summary of all terrain dimensions for frontend dashboard widgets."""
    service = TerrainService.get_instance()
    return service.get_combined_statistics()


@router.get("/3d", summary="Get 3D Terrain Model Metadata & Mesh")
async def get_3d_terrain_info():
    """Retrieve 3D interactive model metadata, HTML viewer link, and downsampled mesh vertices."""
    service = TerrainService.get_instance()
    meta = service.get_elevation_metadata()

    mesh_data = None
    if TERRAIN_MESH_JSON_PATH.is_file():
        try:
            with open(TERRAIN_MESH_JSON_PATH, "r", encoding="utf-8") as f:
                mesh_data = json.load(f)
        except Exception:
            mesh_data = None

    return {
        "html_viewer_url": "/static/jezero_3d_terrain.html",
        "mesh_json_url": "/static/jezero_terrain_mesh.json",
        "vertical_exaggeration": 3.5,
        "elevation_range_m": meta["statistics"],
        "mesh_summary": mesh_data.get("metadata") if mesh_data else "Generate via /api/terrain/3d/generate",
    }


@router.get("/query", response_model=PointQueryResponse, summary="Query Attributes at Point Coordinate")
async def query_point_terrain(
    lon: float = Query(..., ge=-180.0, le=360.0, description="Planetary longitude (°E)"),
    lat: float = Query(..., ge=-90.0, le=90.0, description="Planetary latitude (°N)"),
):
    """Retrieve exact elevation, slope, hazard score, and geological unit for a single point coordinate."""
    service = TerrainService.get_instance()
    result = service.query_point(lon, lat)
    return result
