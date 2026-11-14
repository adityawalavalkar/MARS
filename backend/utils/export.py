"""Export and formatting utilities for routes, rasters, and mission reports."""

from __future__ import annotations

from typing import Any, Dict, List


def create_route_geojson(
    coordinates: List[List[float]],
    properties: Dict[str, Any],
) -> Dict[str, Any]:
    """Create standard RFC 7946 GeoJSON FeatureCollection for a calculated route.

    Coordinates format: [[longitude, latitude, elevation], ...]
    """
    line_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates,
        },
        "properties": {
            "name": properties.get("name", "Mars-Nav Trajectory"),
            "distance_km": properties.get("distance_km", 0.0),
            "duration_hours": properties.get("duration_hours", 0.0),
            "difficulty_score": properties.get("difficulty_score", 0.0),
            "max_slope_deg": properties.get("max_slope_deg", 0.0),
            "avg_slope_deg": properties.get("avg_slope_deg", 0.0),
            "feasibility": properties.get("feasibility", "GO"),
            "mode": properties.get("mode", "rover"),
        },
    }

    start_point = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": coordinates[0] if coordinates else [],
        },
        "properties": {
            "name": "Start Waypoint",
            "type": "start",
        },
    }

    dest_point = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": coordinates[-1] if coordinates else [],
        },
        "properties": {
            "name": "Destination Waypoint",
            "type": "destination",
        },
    }

    return {
        "type": "FeatureCollection",
        "features": [line_feature, start_point, dest_point],
        "metadata": properties,
    }
