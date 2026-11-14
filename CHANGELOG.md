# Change log

## Updated MARS-NAV package

### Terrain analysis
- Replaced raw 3×3 elevation standard deviation with a detrended-plane residual roughness estimate, reducing false roughness caused by regional slope across the window.
- Set hazard categories from slope thresholds (0–5° low, >5–15° moderate, >15° high) and use a 70% slope / 30% roughness score. Added the MOLA resolution limitation in the map/API copy.
- Rebuilt the hazard raster and transparent overlay. Among valid cells, the prior raster was 59.77% low, 22.53% moderate, and 17.71% high; the updated raster is 81.58% low, 17.63% moderate, and 0.79% high. Percentages may not sum exactly due to rounding. The archived raster's high share was 17.71%, not the 17.4% cited in the original request.
- Added and generated a hillshaded MOLA-derived Jezero texture for the 3D terrain view.

### Backend
- Made route slope limits configurable up to 45° while retaining a 15° default, and corrected nearest traversable cell selection to respect the selected limit.
- Added robust zero-length route output and dashboard route comparisons, feasibility, hazard exposure, energy split, and mission-mode consumable estimates.
- Improved continuous terrain-grid resampling, endpoint errors, and configurable local CORS origins.
- Weather now uses supplied local solar time and season, is Jezero-only, and identifies its modeled source. Radiation identifies its Gale-to-Jezero transfer basis.
- Aligned geology labels with USGS SIM 3464 and explicitly marks coarse coordinate lookup results approximate.

### Frontend
- Added NASA Trek MOLA global basemap with CTX and HiRISE local imagery where their published matrix coverage permits, plus layer attribution and raster-bound route-click validation.
- Added planner mission controls, route comparison and feasibility details, and clearer weather, radiation, and mission-report provenance.
- Removed unavailable science overlays and replaced misleading confidence copy.

### Tests and docs
- Added analysis/API checks for hazard calculations, pathfinding policies, mission consumables, geology lookup behavior, endpoint validation, and CORS.
- Added source/limits documentation and these package notes. See `docs/DATA_SOURCES.md` and `README.md`.

## File-by-file record

- `backend/analysis/hazard_assessment.py` — revised residual roughness, slope-only class boundaries, and documented 70/30 score; regenerates the hazard products.
- `backend/config.py` — sets the 15° default traversability policy, configurable local CORS origins, and the generated 3D texture path.
- `backend/analysis/pathfinding.py` — applies per-request slope limits consistently, respects limits when snapping endpoints, and returns a complete zero-length route.
- `backend/services/terrain_service.py` — publishes the class policy and residual-roughness method in hazard response metadata.
- `backend/models/schemas.py` — aligns route slope defaults/limits and supports explanatory hazard threshold metadata.
- `backend/api/routes_dashboard.py` — bilinear continuous grids, approximate Jezero landmark features, modeled region-aware science responses, and expanded route/report analysis.
- `backend/services/science_service.py` — applies seasonal Ls input and labels geology lookup boxes approximate with unmapped fallback and deterministic overlap selection.
- `backend/api/routes_science.py` — passes seasonal Ls through environment prediction.
- `backend/main.py` — disables credentialed wildcard CORS.
- `backend/analysis/realistic_map.py` — generates the local MOLA-derived Jezero texture and hazard imagery.
- `backend/fetch_global_mola_texture.py` — downloads and stitches the selected global MOLA texture matrix based on WMTS GetCapabilities metadata.
- `frontend/src/config.js` — records verified raster bounds and NASA Trek MOLA/CTX/HiRISE matrix, coverage, and zoom configuration.
- `frontend/src/components/dashboard/Map2D.jsx` — uses aligned MOLA/CTX/HiRISE layers, draws comparison routes, and rejects out-of-raster route clicks.
- `frontend/src/components/dashboard/Terrain3D.jsx` — textures the elevation mesh with the backend-served local MOLA product and overlays semi-transparent analytical colors.
- `frontend/src/store/useMarsStore.js` — adds mission controls and preserves structured API error status.
- `frontend/src/services/api.js` — sends Mars24 LTST/Ls, preserves 4xx details, requests planner options, and normalizes expanded route/report payloads.
- `frontend/src/components/dashboard/CenterView.jsx` — adds compact planner controls and route comparison/feasibility/energy details.
- `frontend/src/components/panels/WeatherCard.jsx` and `RadiationCard.jsx` — show modeled provenance, local solar time, and Gale-to-Jezero radiation provenance.
- `frontend/src/components/panels/ReportModal.jsx` — displays difficulty separately from feasibility and only shows applicable per-mode consumables.
- `frontend/src/utils/layers.js` — removes unsupported radiation/mineral grid controls.
- `frontend/src/styles/globals.css` — styles planner controls and imagery attribution.
- `frontend/public/textures/mars.jpg` — replaced with NASA Trek global MOLA color-shaded imagery (4096×2048, equirectangular WMTS mosaic) for the intro globe.
- `tests/test_analysis.py` and `tests/test_api.py` — add slope, hazard, routing, mission, geology, endpoint, and CORS regression coverage.
- `data/processed/jezero_hazard_classes.tif`, `jezero_hazard_score.tif`, `jezero_hazard_map.png`, `jezero_hazard_overlay.png`, and `jezero_mars_terrain_map.png` — regenerated using the revised terrain method.
- `data/processed/jezero_mola_texture.jpg` — generated for the local 3D Jezero mesh.
- `.env.example` — documents the backend CORS origins setting.
- `README.md` — updates fresh setup, validation commands, included assets, data links, and known limits.
- `docs/DATA_SOURCES.md` — records sources, resolution, provenance and interpretation limits.
- `CHANGELOG.md` — records rationale and file-level changes.
- `frontend/src/components/intro/MarsGlobe.jsx` — reduced direct-light intensity and raised soft ambient fill so global MOLA texture relief stays legible.

## Jezero 20 m build
- New Jezero dashboard on the 20 m CTX DEM: slope-limited cost-based A*, radiation-aware (SPE) routing, science-target waypoints (Stack et al. 2020 Table 2), layers (HiRISE, CTX, THEMIS, thermal inertia, CRISM, geology, derived hazard), POV panel, close-up gallery, HUD restyle.
- Removed unsupported "10-50 mSv/hour" SPE claim; SPE multipliers are now x2.0 nominal / x3.0 worst case (Hassler et al. 2018; Zeitlin et al. 2018).
