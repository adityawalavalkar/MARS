# MARS NAV: Jezero 20 m build: run guide

## Run
1. Backend: `pip install -r requirements.txt` then `python run_backend.py` (http://127.0.0.1:8000, docs at /docs).
2. Frontend: `cd frontend && npm install && npm run dev` (Vite proxies /api to the backend). Production: `npm run build`.
3. Flow: intro globe -> global Mars map (only Jezero is clickable; others "coming soon") -> click Jezero -> dashboard -> Calculate.
4. Preprocessing (optional; outputs are already committed): see `docs/JEZERO_PREPROCESSING.md`, then `python backend/scripts/make_hazard_overlay.py`.
5. Tests: `python -m pytest tests -q`.

## New / changed files
- Backend (new): `backend/services/jezero_service.py`, `backend/api/routes_jezero.py` (`GET /api/jezero/config`, `POST /api/jezero/route`, `GET /api/jezero/pov`). Changed: `backend/main.py` (router registered), `backend/services/science_service.py` (unsupported "10-50 mSv/hour" SPE claim removed and replaced by the sourced x2 / x2-3 statement). Existing API routes and contracts are untouched.
- Scripts: `backend/scripts/preprocess_jezero.py`, `make_hazard_overlay.py`.
- Data: `data/config/{science_targets,unit_hazard_costs}.json` (editable), `data/processed/jezero/{jezero_analysis.npz,jezero_terrain_mesh_20m.json}`.
- Frontend (new): `frontend/src/jezero/*` (dashboard, map, 3D terrain, POV, panels, store, HUD css, global-map nomenclature layer) + `public/jezero/*` overlays/JSON + `public/perseverance/*` images. Changed: `components/dashboard/Dashboard.jsx` (Jezero -> new dashboard; legacy dashboard kept for other regions), `Map2D.jsx` (global labels from nomenclature JSON, Jezero outline + pulse, others greyed), `config.js` (THEMIS URLs, global bounds 0-90E 0-44N, vertical exaggeration constant), `vite.config.js` (dev proxy).

## Data honesty
- Hazard = DEM slope + roughness + ASSUMED unit costs: "derived hazard, not measured rock abundance". Thermal inertia is display-only.
- Shielding, walking speed, suit slope limit, shelter (= landing site), dose budget, consumables, stay times, unit costs are ASSUMPTIONS, editable in the UI or JSON.
- Perseverance images have no position; they appear only in the labelled close-up gallery.
- THEMIS Trek tile templates were not testable offline; verify them against each layer's GetCapabilities if tiles do not load.
