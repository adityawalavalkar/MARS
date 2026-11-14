"""NASA scientific data endpoints for HiRISE, CRISM, MEDA Climate, Radiation, and Geology."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

from backend.models.schemas import (
    ClimateResponse,
    RadiationResponse,
    MineralsResponse,
    GeologyResponse,
)
from backend.services.science_service import (
    HiRISEService,
    CRISMService,
    MarsClimateService,
    RadiationService,
    GeologyService,
)

router = APIRouter(prefix="/api", tags=["NASA Scientific Data"])


@router.get("/environment", response_model=ClimateResponse, summary="Get Mars Climate & Atmospheric Conditions")
async def get_environment(
    sol_time_hours: float = Query(12.0, ge=0.0, le=24.66, description="Mars Local True Solar Time (hours)"),
    solar_longitude_ls: float = Query(180.0, ge=0.0, le=360.0, description="Areocentric solar longitude Ls (degrees)"),
):
    """Retrieve Jezero Crater atmospheric baseline (pressure, temperature, wind, dust) and diurnal estimates."""
    baseline = MarsClimateService.get_baseline_climate()
    prediction = MarsClimateService.predict_current_environment(sol_time_hours, solar_longitude_ls)
    return {
        "baseline": baseline,
        "current_prediction": prediction,
    }


@router.get("/radiation", response_model=RadiationResponse, summary="Get Surface Radiation Measurements")
async def get_radiation(
    mission_hours: float = Query(24.0, ge=0.1, le=8760.0, description="Surface mission duration in hours"),
):
    """Retrieve MSL Curiosity RAD surface radiation measurements and cumulative mission dose estimates."""
    calibration = RadiationService.get_radiation_profile()
    mission_exposure = RadiationService.estimate_mission_radiation(mission_hours)
    return {
        "calibration_baseline": calibration,
        "sample_mission_exposure": mission_exposure,
    }


@router.get("/minerals", response_model=MineralsResponse, summary="Get CRISM Mineralogical Observations")
async def get_minerals():
    """Retrieve confirmed CRISM mineralogical detections (smectite, carbonates, olivine) across Jezero Crater."""
    minerals = CRISMService.get_all_minerals()
    return {
        "instrument": "MRO CRISM (Compact Reconnaissance Imaging Spectrometer for Mars)",
        "target_region": "Jezero Crater & Nili Planum Margin",
        "minerals": minerals,
    }


@router.get("/geology", response_model=GeologyResponse, summary="Get USGS Geologic Map Stratigraphy")
async def get_geology():
    """Retrieve USGS SIM 3464 geological map units, ages, and lithology descriptions."""
    citation = GeologyService.get_citation()
    units = GeologyService.get_all_units()
    return {
        "citation": citation,
        "units": units,
    }


@router.get("/hirise", summary="Get HiRISE High-Resolution Mosaic WMTS Endpoint")
async def get_hirise_metadata(
    lon: Optional[float] = Query(None, ge=-180.0, le=360.0, description="Optional planetary longitude (°E) to resolve tile"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Optional planetary latitude (°N) to resolve tile"),
    zoom: int = Query(12, ge=0, le=17, description="WMTS zoom level / TileMatrix (0 to 17)"),
):
    """Retrieve MRO HiRISE 25cm/pixel Jezero mosaic layer ID, WMTS endpoint, and optional resolved tile URL."""
    metadata = dict(HiRISEService.get_metadata())
    if lon is not None and lat is not None:
        row, col = HiRISEService.coords_to_tile(lon, lat, zoom)
        tile_url = HiRISEService.get_tile_url_for_coords(lon, lat, zoom)
        metadata["query_resolution"] = {
            "longitude_deg": lon,
            "latitude_deg": lat,
            "zoom_level": zoom,
            "tile_row": row,
            "tile_col": col,
            "resolved_tile_url": tile_url,
        }
    return metadata
