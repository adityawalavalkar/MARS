"""Pydantic data validation models and schemas for the MARS-NAV API.

Defines strongly-typed request and response structures for terrain queries,
pathfinding navigation, mission resource analysis, and NASA science datasets.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Planetary coordinates in decimal degrees."""
    lon: float = Field(..., ge=-180.0, le=360.0, description="Planetary longitude in degrees East (0° to 360° or -180° to 180°)")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Planetary latitude in degrees North (-90° to 90°)")


class HealthResponse(BaseModel):
    """API health status and raster availability indicator."""
    status: str = Field(default="healthy")
    api_version: str = Field(default="1.0.0")
    study_region: str = Field(default="Jezero Crater, Mars")
    rasters_loaded: bool = Field(default=True)
    memory_efficient_mode: bool = Field(default=True)


class TerrainElevationResponse(BaseModel):
    """Elevation dataset metadata and statistics."""
    dataset_name: str
    source_tile: str
    dimensions: Dict[str, int]
    pixel_resolution_m: Dict[str, float]
    bounds: Dict[str, float]
    statistics: Dict[str, Any]
    raster_file: str
    visualization_file: str


class TerrainSlopeResponse(BaseModel):
    """Slope gradient product statistics and classifications."""
    methodology: str
    statistics: Dict[str, Any]
    thresholds: Dict[str, float]
    distribution: Dict[str, int]
    raster_file: str
    visualization_file: str
    classes_map_file: str


class TerrainHazardsResponse(BaseModel):
    """Terrain hazard classification metadata, statistics, and color codes."""
    classification_scheme: Dict[int, Any]
    statistics: Dict[str, Any]
    thresholds: Dict[str, Any]
    disclaimer: str
    raster_file: str
    score_raster_file: str
    visualization_file: str
    overlay_file: str
    mars_terrain_map_file: str


class TerrainStatsResponse(BaseModel):
    """Comprehensive summary of all terrain dimensions."""
    region: str
    center: Dict[str, float]
    bounds: Dict[str, float]
    elevation: Dict[str, float]
    slope: Dict[str, float]
    hazards: Dict[str, Any]


class PointQueryResponse(BaseModel):
    """Physical and geological attributes queried at a single point coordinate."""
    inside_study_area: bool
    coordinates: Optional[Dict[str, float]] = None
    raster_pixel: Optional[Dict[str, int]] = None
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    hazard_class: Optional[int] = None
    hazard_name: Optional[str] = None
    hazard_score: Optional[float] = None
    traversable: Optional[bool] = None
    geological_unit: Optional[Dict[str, Any]] = None
    detected_minerals: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class RoutePlanRequest(BaseModel):
    """Parameters for planning a candidate surface route."""
    start: Coordinates
    destination: Coordinates
    safety_weight: float = Field(default=1.5, ge=0.0, le=10.0, description="Hazard penalty multiplier: 0.5 (fastest), 1.5 (balanced), 3.0+ (safest)")
    max_slope_limit: float = Field(default=15.0, ge=5.0, le=45.0, description="Default blocks hazard class 2 (>15°); explicit requests may permit up to 45°")
    mode: Literal["rover", "crewed", "eva"] = Field(default="rover", description="Mobility mode: 'rover' (robotic), 'crewed' (pressurized rover), 'eva' (astronaut walking)")
    vehicle_mass_kg: Optional[float] = Field(default=None, description="Optional custom vehicle/payload mass in kg")
    crew_size: int = Field(default=2, ge=1, le=6, description="Astronaut crew count for life support estimation")
    battery_capacity_kwh: Optional[float] = Field(default=None, description="Optional battery storage capacity in kWh")


class RoutePlanResponse(BaseModel):
    """Detailed pathfinding route output including GeoJSON and mission analysis."""
    success: bool
    summary: Dict[str, Any]
    waypoints: List[List[float]]
    path_details: List[Dict[str, Any]]
    geojson: Dict[str, Any]
    mission_analysis: Dict[str, Any]


class ClimateResponse(BaseModel):
    """Mars Environmental Dynamics Analyzer (MEDA) atmospheric baseline and predictions."""
    baseline: Dict[str, Any]
    current_prediction: Optional[Dict[str, Any]] = None


class RadiationResponse(BaseModel):
    """Surface radiation measurements (MSL RAD) and exposure models."""
    calibration_baseline: Dict[str, Any]
    sample_mission_exposure: Dict[str, Any]


class MineralsResponse(BaseModel):
    """CRISM targeted spectrometry mineralogy catalog for Jezero Crater."""
    instrument: str
    target_region: str
    minerals: List[Dict[str, Any]]


class GeologyResponse(BaseModel):
    """USGS SIM 3464 geological map stratigraphy and citations."""
    citation: Dict[str, Any]
    units: List[Dict[str, Any]]
