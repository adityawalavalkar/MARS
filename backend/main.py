"""MARS-NAV FastAPI Application Entrypoint.

Provides geospatial terrain analysis, A* route planning, mission resource estimation,
and NASA planetary science endpoints for the Jezero Crater exploration dashboard.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import (
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    CORS_ORIGINS,
    PROCESSED_DIR,
    HAZARD_CLASSES_RASTER_PATH,
    MARS_TERRAIN_MAP_PATH,
    TERRAIN_3D_HTML_PATH,
)
from backend.models.schemas import HealthResponse
from backend.services.terrain_service import TerrainService
from backend.api import routes_terrain, routes_navigation, routes_mission, routes_science, routes_dashboard, routes_jezero

FRONTEND_DIST_DIR = _REPO_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm in-memory terrain rasters and verify required assets at server startup."""
    print("MARS-NAV Backend starting up...")
    print(f"Data directory: {PROCESSED_DIR}")

    # Initialize TerrainService singleton to pre-load rasters into memory
    service = TerrainService.get_instance()
    print("Pre-warmed Jezero MOLA rasters into memory cache.")
    print(f"Study bounds: {service.pathfinder.bounds_deg}")
    print("MARS-NAV Backend is ready for frontend connections!")
    yield
    print("MARS-NAV Backend shutting down...")


# Initialize FastAPI application
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for full frontend accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for direct image, GeoTIFF, and 3D HTML delivery
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(PROCESSED_DIR)), name="static")

# Include Modular Routers
app.include_router(routes_terrain.router)
app.include_router(routes_navigation.router)
app.include_router(routes_mission.router)
app.include_router(routes_science.router)
app.include_router(routes_dashboard.router)
app.include_router(routes_jezero.router)


@app.get("/api", summary="MARS-NAV API Overview")
@app.get("/", summary="MARS-NAV Overview", include_in_schema=False)
async def root_overview():
    """Serve the production dashboard, or API overview when no frontend build exists."""
    if FRONTEND_DIST_DIR.is_dir():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
    return {
        "project": "MARS-NAV",
        "description": "Regional Mars exploration overview with detailed Jezero terrain analysis and safe navigation.",
        "version": API_VERSION,
        "status": "OPERATIONAL",
        "interactive_3d_terrain": "/static/jezero_3d_terrain.html",
        "mars_terrain_map": "/static/jezero_mars_terrain_map.png",
        "hazard_map": "/static/jezero_hazard_map.png",
        "hazard_overlay": "/static/jezero_hazard_overlay.png",
        "api_documentation": "/docs",
        "core_endpoints": [
            "GET  /api/health",
            "GET  /api/terrain/elevation",
            "GET  /api/terrain/regional",
            "GET  /api/terrain/regional/grid?south=12&west=65&north=27&east=90",
            "GET  /api/terrain/regional/features",
            "GET  /api/terrain/slope",
            "GET  /api/terrain/hazards",
            "GET  /api/terrain/statistics",
            "GET  /api/terrain/3d",
            "GET  /api/terrain/query?lon=77.45&lat=18.44",
            "POST /api/route/plan",
            "GET  /api/route/samples",
            "GET  /api/mission/report",
            "POST /api/mission/analyze",
            "GET  /api/environment",
            "GET  /api/radiation",
            "GET  /api/minerals",
            "GET  /api/geology",
            "GET  /api/hirise",
        ],
    }


if FRONTEND_DIST_DIR.is_dir():
    # Production Docker image includes the Vite build. Serving it from the API
    # origin keeps browser requests same-origin and preserves public assets such
    # as /jezero/* alongside the React app. Register this catch-all last.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """System health check and raster availability verification."""
    return HealthResponse(
        status="healthy",
        api_version=API_VERSION,
        study_region="Jezero Crater, Mars (18.4°N, 77.7°E)",
        rasters_loaded=True,
        memory_efficient_mode=True,
    )


if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    print(f"Starting server on http://{HOST}:{PORT}")
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
