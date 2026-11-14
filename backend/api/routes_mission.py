"""Mission analysis and feasibility report API endpoints."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from backend.models.schemas import RoutePlanRequest
from backend.services.terrain_service import TerrainService
from backend.analysis.mission import calculate_mission_analysis
from backend.config import OCTAVIA_E_BUTLER_LANDING_LON, OCTAVIA_E_BUTLER_LANDING_LAT

router = APIRouter(prefix="/api/mission", tags=["Mission Analysis"])


@router.get("/report", summary="Get Baseline Mission Analysis Report")
async def get_default_mission_report():
    """Retrieve an operational mission report for a baseline traverse from the landing site to the delta."""
    service = TerrainService.get_instance()
    try:
        route_result = service.pathfinder.plan_route(
            start_lon=OCTAVIA_E_BUTLER_LANDING_LON,
            start_lat=OCTAVIA_E_BUTLER_LANDING_LAT,
            dest_lon=77.6200,
            dest_lat=18.4100,
            mode="rover",
        )
        report = calculate_mission_analysis(route_result)
        return {
            "mission_name": "Jezero Crater Floor Exploration Traverse",
            "route_summary": route_result["summary"],
            "analysis": report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mission calculation error: {str(e)}")


@router.post("/analyze", summary="Analyze Mission Requirements for Custom Trajectory")
async def analyze_custom_mission(request: RoutePlanRequest):
    """Compute detailed mission energy, consumables, radiation, and feasibility for custom parameters."""
    service = TerrainService.get_instance()
    try:
        route_result = service.pathfinder.plan_route(
            start_lon=request.start.lon,
            start_lat=request.start.lat,
            dest_lon=request.destination.lon,
            dest_lat=request.destination.lat,
            safety_weight=request.safety_weight,
            max_slope_limit=request.max_slope_limit,
            mode=request.mode,
        )
        report = calculate_mission_analysis(
            route_result=route_result,
            vehicle_mass_kg=request.vehicle_mass_kg,
            crew_size=request.crew_size,
            battery_capacity_kwh=request.battery_capacity_kwh,
        )
        return {
            "route_summary": route_result["summary"],
            "analysis": report,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
