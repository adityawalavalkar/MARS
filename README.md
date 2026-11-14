# MARS-NAV

MARS-NAV is a FastAPI and React/Vite dashboard for Jezero Crater and the Nili–Isidis regional overview. It includes the processed terrain rasters and map assets used by the application.

## Run from a fresh checkout

Requirements: Python 3.10+, Node.js 20.19+ (or 22.12+) and npm.

```powershell
# Terminal 1 — project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_backend.py

# Terminal 2 — project root
Copy-Item frontend\.env.example frontend\.env
Set-Location frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The frontend `.env.example` points to the backend at `http://localhost:8000`. For non-local deployments, configure `VITE_API_BASE_URL` and `MARS_NAV_CORS_ORIGINS` to the intended frontend origin(s).

## Verification

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm run lint
npm run build
```

## Public single-URL deployment (Render)

The Docker image builds the React/Vite app and serves it from the FastAPI origin, so the dashboard, API, Jezero static assets and `/static` terrain products share one URL. No `VITE_API_BASE_URL` or production CORS configuration is needed. NASA Trek basemap tiles still load directly from NASA in visitors' browsers.

1. Push this project to a GitHub repository connected to Render.
2. In Render, create a Blueprint from that repository and select `render.yaml`.
3. Wait for the Docker build and `/api/health` health check to pass; open the service's `onrender.com` URL.

The included Blueprint uses Render's free web service plan. Free services can sleep when idle, so the first visit after inactivity may take longer while the backend starts and loads terrain data. The deployment bundles the processed data and does not require persistent storage.

## Included data

- Processed Jezero MOLA elevation, slope, hazard class/score GeoTIFFs and derived map/overlay imagery.
- NASA Trek global MOLA color-shaded image for the intro globe and regional fallback, plus the processed regional MOLA overview.
- CTX and HiRISE images are loaded from NASA Trek WMTS where the layer coverage and network are available.
- A MOLA-derived local texture and mesh data for Jezero 3D terrain.

No raw MOLA PDS source download is needed to run the application. The optional source/regeneration workflow is described in `docs/REGIONAL_MAPPING.md`.

## Known limits

- The Jezero terrain raster is approximately 463 m/pixel. Slope and detrended residual roughness are regional screening proxies; rover-scale hazards are unresolved.
- Weather is a time and season varying modeled estimate (MEDA-based), not a live feed or forecast. Radiation is a modeled Gale-to-Jezero transfer estimate based on MSL RAD calibration.
- Geology lookup coordinates are approximate bounding-box aids based on USGS SIM 3464, not digitized map contacts.
- Route feasibility, energy and crew resources depend on simplified planning assumptions and are not certified vehicle limits.
- Online NASA Trek imagery requires network access; local MOLA and Jezero products remain available offline.

See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for source URLs, resolution, provenance and credit notes.
