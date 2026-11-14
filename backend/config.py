"""MARS-NAV Central Configuration.

Defines repository paths, geospatial constants for Mars, hazard thresholds,
navigation defaults, and mission parameters. All paths are resolved dynamically
relative to the repository root to ensure full portability across environments.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repository root dynamically resolved
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

# Data directories
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = REPO_ROOT / "outputs"

# Raw dataset paths
MOLA_RAW_DIR = RAW_DIR / "MOLA"
MOLA_RAW_IMG = MOLA_RAW_DIR / "megt44n000hb.img"
CTX_RAW_DIR = RAW_DIR / "CTX"
HIRISE_RAW_DIR = RAW_DIR / "HiRISE"
THEMIS_RAW_DIR = RAW_DIR / "THEMIS"

# Processed raster products
ELEVATION_RASTER_PATH = PROCESSED_DIR / "jezero_mola_elevation.tif"
SLOPE_RASTER_PATH = PROCESSED_DIR / "jezero_slope.tif"
HAZARD_CLASSES_RASTER_PATH = PROCESSED_DIR / "jezero_hazard_classes.tif"
HAZARD_SCORE_RASTER_PATH = PROCESSED_DIR / "jezero_hazard_score.tif"

# Processed visualization products
ELEVATION_MAP_PATH = PROCESSED_DIR / "jezero_elevation_map.png"
SLOPE_MAP_PATH = PROCESSED_DIR / "jezero_slope_map.png"
SLOPE_CLASSES_MAP_PATH = PROCESSED_DIR / "jezero_slope_classes.png"
HAZARD_MAP_PATH = PROCESSED_DIR / "jezero_hazard_map.png"
HAZARD_OVERLAY_PATH = PROCESSED_DIR / "jezero_hazard_overlay.png"
MARS_TERRAIN_MAP_PATH = PROCESSED_DIR / "jezero_mars_terrain_map.png"
MOLA_TEXTURE_PATH = PROCESSED_DIR / "jezero_mola_texture.jpg"
SAMPLE_ROUTE_MAP_PATH = PROCESSED_DIR / "jezero_sample_route.png"
TERRAIN_3D_HTML_PATH = PROCESSED_DIR / "jezero_3d_terrain.html"
TERRAIN_MESH_JSON_PATH = PROCESSED_DIR / "jezero_terrain_mesh.json"

# Regional overview products.  These are deliberately separate from the
# high-detail Jezero analysis rasters above: they are used for lightweight map
# browsing only and are never fed into slope, hazard, or route calculations.
REGIONAL_BOUNDS = {"west": 65.0, "east": 90.0, "south": 12.0, "north": 27.0}
REGIONAL_OVERVIEW_PATH = PROCESSED_DIR / "regional_mola_overview.tif"
REGIONAL_PREVIEW_WEBP_PATH = PROCESSED_DIR / "regional_mola_overview.webp"
REGIONAL_OVERVIEW_MAX_WIDTH = 640
REGIONAL_GRID_MAX_RESOLUTION = 512
REGIONAL_GRID_CACHE_SIZE = 12

# Verified from the local MEGDR header/raster metadata, not from a download.
MOLA_SOURCE_COVERAGE = {"west": 0.0, "east": 90.0, "south": 0.0, "north": 44.0}

# Display extents are clipped excerpts of the USGS/I AU Gazetteer geometries.
# They are orientation aids, not geology polygons or analysis masks.  Their
# source URLs are returned by the regional API and documented for the UI.
REGIONAL_FEATURES = [
    {
        "id": "jezero", "name": "Jezero Crater", "kind": "Crater",
        "bounds": {"west": 77.30, "east": 78.10, "south": 18.10, "north": 18.90},
        "source": "https://planetarynames.wr.usgs.gov/Feature/14300",
    },
    {
        "id": "nili-fossae", "name": "Nili Fossae", "kind": "Fossae",
        "bounds": {"west": 72.10, "east": 81.70, "south": 17.01, "north": 27.12},
        "source": "https://planetarynames.wr.usgs.gov/Feature/4271",
    },
    {
        "id": "syrtis-major", "name": "Syrtis Major Planum", "kind": "Planum",
        "bounds": {"west": 65.0, "east": 77.00, "south": 12.0, "north": 18.79},
        "source": "https://planetarynames.wr.usgs.gov/Feature/5796",
    },
    {
        "id": "isidis", "name": "Isidis Planitia", "kind": "Planitia",
        "bounds": {"west": 77.00, "east": 90.0, "south": 12.0, "north": 22.76},
        "source": "https://planetarynames.wr.usgs.gov/Feature/2735",
    },
    {
        "id": "terra-sabaea", "name": "Terra Sabaea", "kind": "Terra",
        "bounds": {"west": 65.0, "east": 85.0, "south": 12.0, "north": 27.0},
        "source": "https://planetarynames.wr.usgs.gov/Feature/5931",
    },
    {
        "id": "neretva", "name": "Neretva Vallis", "kind": "Vallis",
        "bounds": {"west": 77.00, "east": 77.30, "south": 18.50, "north": 18.60},
        "source": "https://planetarynames.wr.usgs.gov/Feature/15879",
    },
    {
        "id": "sava", "name": "Sava Vallis", "kind": "Vallis",
        "bounds": {"west": 76.69, "east": 77.56, "south": 18.74, "north": 19.43},
        "source": "https://planetarynames.wr.usgs.gov/Feature/15904",
    },
    {
        "id": "pliva", "name": "Pliva Vallis", "kind": "Vallis",
        "bounds": {"west": 78.09, "east": 78.60, "south": 18.52, "north": 18.81},
        "source": "https://planetarynames.wr.usgs.gov/Feature/15903",
    },
]

# Mars Physical Constants
MARS_RADIUS_M = 3389500.0  # Mars mean radius specified for mission calculations (m)
MARS_GRAVITY_MS2 = 3.721   # Surface gravitational acceleration in m/s²
MARS_SOL_HOURS = 24.6598   # 1 Martian Sol = 24 hours 39 minutes 35.244 seconds
MARS_SOL_SECONDS = MARS_SOL_HOURS * 3600.0

# Jezero Crater Geographic Landmarks (Degrees Planetocentric)
JEZERO_CENTER_LAT = 18.40625
JEZERO_CENTER_LON = 77.69531
JEZERO_DELTA_LAT = 18.4447
JEZERO_DELTA_LON = 77.4508
PERSEVERANCE_LANDING_LAT = 18.4447
PERSEVERANCE_LANDING_LON = 77.4508
OCTAVIA_E_BUTLER_LANDING_LAT = 18.4446
OCTAVIA_E_BUTLER_LANDING_LON = 77.4509
SEITAH_LAT = 18.4350
SEITAH_LON = 77.4420
NERETVA_VALLIS_INLET_LAT = 18.5200
NERETVA_VALLIS_INLET_LON = 77.3400
CRATER_RIM_NORTH_LAT = 18.6200
CRATER_RIM_NORTH_LON = 77.5800

# Raster Processing Values
SLOPE_NODATA_VALUE = -9999.0
HAZARD_NODATA_VALUE = 255
HAZARD_SCORE_NODATA_VALUE = -9999.0

# Hazard Classification Thresholds (Degrees)
# Documented project-defined bins, illustrative for exploration planning
SLOPE_GENTLE_MAX = 5.0     # 0 to 5 deg: Safe, nominal traverse
SLOPE_MODERATE_MAX = 15.0  # 5 to 15 deg: Moderate hazard, requires caution
SLOPE_STEEP_MAX = 25.0     # 15 to 25 deg: Severe hazard, impassable for standard rovers
MAX_TRAVERSABLE_SLOPE = 15.0  # Default blocks class 2; requests may explicitly allow up to 45°.

# Hazard Class Definitions
HAZARD_CLASSES = {
    0: {
        "name": "Safe / Low Hazard",
        "description": "Gentle plains, crater floor, slopes 0–5°. Nominal traverse.",
        "color": "#2ca02c",  # Green
        "traversable": True,
        "base_cost_multiplier": 1.0,
    },
    1: {
        "name": "Moderate Hazard",
        "description": "Rolling terrain, hummocks, slopes 5–15°. Reduced speed required.",
        "color": "#ff7f0e",  # Orange
        "traversable": True,
        "base_cost_multiplier": 2.5,
    },
    2: {
        "name": "Severe / High Hazard",
        "description": "Slopes > 15°. Impassable by default; an explicit higher route slope limit can allow them.",
        "color": "#d62728",  # Red
        "traversable": False,  # Impassable by default unless high-mobility configured
        "base_cost_multiplier": 10.0,
    },
    255: {
        "name": "Restricted / NoData",
        "description": "Dataset boundary or invalid sensor data. Strictly non-traversable.",
        "color": "#7f7f7f",  # Gray
        "traversable": False,
        "base_cost_multiplier": float("inf"),
    },
}

# Mission Default Parameters
DEFAULT_ROVER_MASS_KG = 1025.0       # Perseverance class rover mass in kg
DEFAULT_CREW_ROVER_MASS_KG = 2800.0  # Small Pressurized Rover (SPR) class mass in kg
DEFAULT_ASTRONAUT_EVA_MASS_KG = 145.0  # Astronaut + EMU spacesuit in kg

DEFAULT_NOMINAL_SPEED_ROVER_KMH = 0.15     # 150 m/h nominal rover drive speed
DEFAULT_NOMINAL_SPEED_CREWED_KMH = 4.5     # 4.5 km/h crewed rover speed
DEFAULT_NOMINAL_SPEED_EVA_KMH = 1.8        # 1.8 km/h astronaut walking on Mars

# API & Server Settings
API_TITLE = "MARS-NAV Backend API"
API_VERSION = "1.1.0"
API_DESCRIPTION = (
    "Regional MOLA exploration map with detailed Jezero-only navigation, terrain hazard "
    "assessment, and mission analysis. Powered by NASA MOLA, CTX, HiRISE, CRISM, MEDA, and MSL RAD data."
)
HOST = os.getenv("MARS_NAV_HOST", "0.0.0.0")
PORT = int(os.getenv("MARS_NAV_PORT", "8000"))
CORS_ORIGINS = [origin.strip() for origin in os.getenv(
    "MARS_NAV_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
).split(",") if origin.strip()]
