import math

import numpy as np
import rasterio
from rasterio.warp import transform

from backend.analysis.hazard_assessment import classify_terrain_hazards
from backend.analysis.pathfinding import MarsPathfinder
from backend.analysis.mission import calculate_mission_analysis
from backend.config import ELEVATION_RASTER_PATH, SLOPE_RASTER_PATH
from backend.services.science_service import GeologyService


def test_slope_matches_independent_horn_recompute():
    with rasterio.open(ELEVATION_RASTER_PATH) as dem, rasterio.open(SLOPE_RASTER_PATH) as slope_src:
        z = dem.read(1).astype(np.float64)
        saved = slope_src.read(1)[1:-1, 1:-1]
        affine = dem.transform
        center_rows = np.arange(1, z.shape[0] - 1)
        northing = affine.f + affine.e * (center_rows + 0.5)
        _, latitudes = transform(
            dem.crs, dem.crs.geodetic_crs,
            [affine.c] * len(northing), northing,
        )
        dx = abs(affine.a) * np.cos(np.deg2rad(latitudes))
        dy = abs(affine.e)
        nw, n, ne = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
        w, e = z[1:-1, :-2], z[1:-1, 2:]
        sw, s, se = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
        dzdx = ((ne + 2 * e + se) - (nw + 2 * w + sw)) / (8 * dx[:, None])
        dzdy = ((sw + 2 * s + se) - (nw + 2 * n + ne)) / (8 * dy)
        recomputed = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
        valid = np.isfinite(saved) & (saved >= 0) & np.isfinite(recomputed)
        assert valid.sum() > 60_000
        assert np.max(np.abs(saved[valid] - recomputed[valid])) < 0.001


def test_hazard_bins_depend_only_on_slope_and_score_is_70_30():
    slope = np.array([[0.0, 5.0, 5.1, 15.0, 15.1]], dtype=np.float32)
    roughness = np.array([[50.0, 0.0, 50.0, 0.0, 0.0]], dtype=np.float32)
    elevation = np.zeros_like(slope)
    classes, scores = classify_terrain_hazards(slope, roughness, elevation, None)
    assert classes.tolist() == [[0, 0, 1, 1, 2]]
    expected = 0.70 * np.clip(slope / 25.0, 0, 1) + 0.30 * np.clip(roughness / 50.0, 0, 1)
    np.testing.assert_allclose(scores, expected, atol=1e-6)


def test_hazard_classes_cover_valid_cells_and_match_slope_thresholds():
    with rasterio.open(SLOPE_RASTER_PATH) as src:
        slope = src.read(1)
    with rasterio.open(ELEVATION_RASTER_PATH) as src:
        elevation = src.read(1)
        nodata = src.nodata
    roughness = np.zeros_like(slope)
    classes, _ = classify_terrain_hazards(slope, roughness, elevation, nodata)
    valid = np.isfinite(slope) & (slope >= 0) & (slope != -9999.0)
    assert np.all(classes[valid & (slope <= 5)] == 0)
    assert np.all(classes[valid & (slope > 5) & (slope <= 15)] == 1)
    assert np.all(classes[valid & (slope > 15)] == 2)


def test_pathfinder_same_pixel_out_of_bounds_and_safety_weight_effect():
    finder = MarsPathfinder()
    same = finder.pixel_to_coords(128, 128)
    result = finder.plan_route(*same, *same)
    assert result["summary"]["distance_km"] == 0
    assert result["summary"]["difficulty_score"] == 0
    assert result["path_details"]
    assert len(result["geojson"]["features"][0]["geometry"]["coordinates"]) == 2

    try:
        finder.plan_route(-10, 0, *same)
    except ValueError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("out-of-bounds coordinates must fail")

    start = finder.pixel_to_coords(30, 100)
    end = finder.pixel_to_coords(220, 160)
    fast = finder.plan_route(*start, *end, safety_weight=0.5)
    safe = finder.plan_route(*start, *end, safety_weight=3.0)
    assert fast["summary"]["safety_weight"] == 0.5
    assert safe["summary"]["safety_weight"] == 3.0
    assert fast["waypoints"] != safe["waypoints"]


def test_mission_analysis_has_mode_specific_consumables():
    finder = MarsPathfinder()
    start = finder.pixel_to_coords(128, 128)
    end = finder.pixel_to_coords(130, 130)
    analyses = {}
    for mode in ("rover", "crewed", "eva"):
        route = finder.plan_route(*start, *end, mode=mode)
        analyses[mode] = calculate_mission_analysis(route, crew_size=2)
        assert analyses[mode]["energy_requirements"]["propulsion_energy_kwh"] >= 0
        assert analyses[mode]["energy_requirements"]["hotel_load_energy_kwh"] >= 0
    assert analyses["rover"]["life_support_consumables"]["applicable"] is False
    assert analyses["crewed"]["life_support_consumables"]["estimated_total_water_liters"] is not None
    assert analyses["crewed"]["life_support_consumables"]["estimated_oxygen_consumed_kg"] is not None
    assert analyses["eva"]["life_support_consumables"]["estimated_total_water_liters"] is not None


def test_geology_uses_official_symbols_approximate_boxes_and_unmapped_outside():
    assert GeologyService.query_geology_at_coords(77.45, 18.44)["unit_symbol"] == "NHjf₂"
    assert GeologyService.query_geology_at_coords(77.45, 18.44)["approximate"] is True
    assert GeologyService.query_geology_at_coords(77.60, 18.46)["unit_symbol"] == "unmapped"
