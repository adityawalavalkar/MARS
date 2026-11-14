import pytest
from fastapi.testclient import TestClient

from backend.config import CORS_ORIGINS
from backend.main import app
from backend.analysis.pathfinding import MarsPathfinder


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_api_get_routes_return_success(client):
    paths = [
        "/", "/api/health", "/api/route/samples", "/api/terrain/regional",
        "/api/terrain/regional/features", "/api/terrain/elevation", "/api/terrain/slope",
        "/api/terrain/hazards", "/api/terrain/statistics", "/api/terrain/3d",
        "/api/terrain/query?lon=77.4508&lat=18.4447", "/api/environment",
        "/api/radiation", "/api/minerals", "/api/geology", "/api/hirise",
        "/api/composition", "/api/mineral-ratio",
        "/api/weather?regionId=jezero&sol_time_hours=13.2&solar_longitude_ls=180&longitude_deg=77.45",
        "/api/dashboard/radiation?regionId=jezero",
        "/api/hazard-grid?south=18.2&west=77.3&north=18.7&east=77.8&resolution=16",
        "/api/elevation-grid?south=18.2&west=77.3&north=18.7&east=77.8&resolution=16",
        "/api/terrain/regional/grid?south=18&west=77&north=18.5&east=77.5&resolution=16",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, f"{path}: {response.status_code} {response.text}"


def test_api_post_routes_return_success(client):
    finder = MarsPathfinder()
    lon, lat = finder.pixel_to_coords(128, 128)
    coordinates = {"lon": lon, "lat": lat}
    dashboard = client.post("/api/route", json={"start": coordinates, "end": coordinates, "mode": "rover"})
    assert dashboard.status_code == 200, dashboard.text
    feature = dashboard.json()
    assert feature["geometry"]["type"] == "LineString"
    assert len(feature["geometry"]["coordinates"]) == 2

    payload = {"start": coordinates, "destination": coordinates, "mode": "crewed", "crew_size": 2}
    plan = client.post("/api/route/plan", json=payload)
    assert plan.status_code == 200, plan.text
    assert plan.json()["summary"]["distance_km"] == 0

    profile = client.post("/api/elevation-profile", json={"route": feature})
    assert profile.status_code == 200, profile.text
    report = client.post("/api/mission-report", json={"route": feature})
    assert report.status_code == 200, report.text
    analysis = client.post("/api/mission/analyze", json=payload)
    assert analysis.status_code == 200, analysis.text


def test_invalid_requests_return_clear_4xx(client):
    response = client.get("/api/weather?regionId=regional&sol_time_hours=12&solar_longitude_ls=180&longitude_deg=77.4")
    assert response.status_code == 422
    assert "Jezero-only" in response.json()["detail"]

    response = client.get("/api/hazard-grid?south=-80&west=0&north=-70&east=5")
    assert response.status_code == 422
    assert "Jezero" in response.json()["detail"]

    response = client.post("/api/route", json={"start": {"lon": -10, "lat": 0}, "end": {"lon": 77.5, "lat": 18.4}})
    assert response.status_code == 400
    assert "outside" in response.json()["detail"]


def test_cors_is_restricted_and_credentials_are_disabled():
    assert "*" not in CORS_ORIGINS
    middleware = next(item for item in app.user_middleware if item.cls.__name__ == "CORSMiddleware")
    assert middleware.kwargs["allow_credentials"] is False
