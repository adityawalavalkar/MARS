"""Navigation and pathfinding API endpoints for Mars surface route planning."""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

from backend.models.schemas import RoutePlanRequest, RoutePlanResponse
from backend.services.terrain_service import TerrainService
from backend.analysis.mission import calculate_mission_analysis

router = APIRouter(prefix="/api/route", tags=["Navigation & Pathfinding"])


@router.post("/plan", response_model=RoutePlanResponse, summary="Calculate Safe Trajectory using A*")
async def plan_route(request: RoutePlanRequest):
    """Calculate an optimal, safe surface trajectory between two Martian coordinates.

    Uses A* search over MOLA elevation gradients and terrain hazard classifications.
    Returns:
    - GeoJSON LineString and Point features
    - Step-by-step waypoint profile with elevation, slope, and hazard scores
    - Integrated mission analysis (energy, consumables, radiation, feasibility)
    """
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

        mission_analysis = calculate_mission_analysis(
            route_result=route_result,
            vehicle_mass_kg=request.vehicle_mass_kg,
            crew_size=request.crew_size,
            battery_capacity_kwh=request.battery_capacity_kwh,
        )

        return {
            "success": True,
            "summary": route_result["summary"],
            "waypoints": route_result["waypoints"],
            "path_details": route_result["path_details"],
            "geojson": route_result["geojson"],
            "mission_analysis": mission_analysis,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=422, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing computation error: {str(e)}")


@router.get("/samples", summary="Get Predefined Jezero Scientific Traverses")
async def get_sample_routes():
    """Retrieve pre-configured scientific routes representing Perseverance and human exploration sorties."""
    service = TerrainService.get_instance()
    return service.get_sample_routes()
