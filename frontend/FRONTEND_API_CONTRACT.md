# MARS NAV — Frontend ⇄ Backend API contract

The frontend (`src/services/api.js`) calls these endpoints. Paths live in the `endpoints` object at the top of that file — change them there if your routes differ.
Base URL: `VITE_API_BASE_URL` (e.g. `http://localhost:8000`). Enable **CORS** for the frontend origin.

**Rules**
- JSON in / JSON out. Any non-2xx, timeout (8 s), empty or malformed body → the UI shows its empty/error state (no fallback data exists in the app).
- Units: wind **km/h**, temperature **°C**, radiation **µSv/h**, elevation **meters**, slope **degrees**, ratios/fractions **0–1**, coordinates **decimal degrees** (east-positive longitude).
- Routes are **GeoJSON** (`[lon, lat]` order inside GeoJSON; everything else uses `lat`, `lon` keys).
- **Grids:** either flat `values` + `width` + `height`, or `values` as a 2D array (rows). **Row 0 = NORTH edge, column 0 = WEST edge.** `bounds` = `{south, west, north, east}` (or `[[south, west], [north, east]]`). Use `null` for missing cells.
- `region` is the object in `src/config.js` (`DEFAULT_REGION`); it is sent as query params `regionId`, `lat`, `lon` (region centre).

## Regional overview endpoints

The application opens at **65–90°E / 12–27°N** and uses display-only MOLA data. These endpoints do not perform regional hazards, pathfinding, or 3D terrain generation.

- `GET /api/terrain/regional` returns coverage and GeoTIFF metadata.
- `GET /api/terrain/regional/features` returns GeoJSON orientation labels/boundaries for the named regional context.
- `GET /api/terrain/regional/grid?south=&west=&north=&east=&resolution=` returns only the current Leaflet viewport. The server keeps a small LRU cache of recent grids.

When the viewport reaches Jezero at high zoom, the frontend requests CTX WMTS tiles directly from NASA Trek. The Jezero analysis endpoints below remain unchanged.

---

## 1. `GET /api/weather?regionId=&lat=&lon=`  (NASA atmospheric data)
```json
{ "windSpeedKmh": 36, "temperatureC": -63 }
```
Polled every 30–60 s (Machine Settings).

## 2. `GET /api/dashboard/radiation?regionId=&lat=&lon=`  (NASA RAD dashboard payload)
```json
{
  "doseRateUSvH": 27.0,
  "source": "MSL RAD calibration baseline",
  "missionHours": 24.0
}
```
Polled like weather. The supplied scientific model provides a regional baseline, not a radiation raster.

## 3. `GET /api/hazard-grid?south=&west=&north=&east=`  (MOLA elevation + slope classification)
```json
{
  "bounds": {"south":18.2,"west":77.3,"north":18.7,"east":77.8},
  "width": 64, "height": 64,
  "values": [0.0, 0.12],
  "summary": { "level": "Low|Medium|High", "score": 0.54, "confidence": 0.78 }
}
```
`values`: hazard score 0 (safe) … 1 (extreme). `summary` is optional. If `score` is missing the UI uses the grid mean; if `level` is missing it is derived (<0.33 Low, <0.66 Medium, else High). `confidence` feeds the "Confidence %" stat.

## 4. `GET /api/elevation-grid?south=&west=&north=&east=&resolution=128`  (heightmap + terrain model)
```json
{
  "bounds": {"south":18.2,"west":77.3,"north":18.7,"east":77.8},
  "width": 128, "height": 128,
  "values": [-2610.5, -2608.1],
  "slope": [3.2, 4.0],
  "features": [ { "label": "Delta front", "lat": 18.5, "lon": 77.55 } ]
}
```
`values` in meters; `slope` in degrees with the same width/height. Builds the 3D mesh, the 3D-projection wireframe, the Elevation/Slope layers and the hover readout. `slope` and `features` are optional.

## 5. `POST /api/elevation-profile`  (elevation along the route)
Request: `{ "route": <GeoJSON Feature returned by /api/route> }`
```json
{ "distancesKm": [0, 0.5, 1.0], "elevations": [-2600, -2590, -2575], "min": -2600, "max": -2200 }
```
Arrays must be equal length (≥ 2). `min`/`max` optional.

## 6. `GET /api/composition?regionId=&lat=&lon=`  (CRISM detection catalog)
```json
{ "components": [ { "name": "Fe/Mg Smectite Clay", "confidence": "HIGH" } ], "basis": "CRISM detection catalog; not mineral abundance" }
```
`confidence` is taken directly from the curated CRISM catalog. The dashboard does not imply an unsupported mineral abundance calculation.

## 7. `GET /api/mineral-ratio?regionId=&lat=&lon=`  (CRISM catalog compatibility)
```json
{
  "ratio": null,
  "minerals": [ { "name": "Fe/Mg Smectite Clay", "confidence": "HIGH" } ],
  "basis": "No mineral abundance ratio is available from the curated CRISM catalog."
}
```
The supplied backend has confirmed mineral detections but no abundance-ratio raster, so the UI accurately displays catalog confidence instead of fabricating a ratio.

## 8. `POST /api/route`  (path planning)
Request: `{ "start": {"lat": 18.34, "lon": 77.48}, "end": {"lat": 18.37, "lon": 77.61} }`
```json
{
  "type": "Feature",
  "geometry": { "type": "LineString", "coordinates": [[77.48, 18.34], [77.52, 18.35]] },
  "properties": {
    "distanceKm": 12.4,
    "durationHours": 3.5,
    "difficulty": "Easy|Moderate|Hard|Extreme",
    "waypoints": [ { "lat": 18.35, "lon": 77.52 } ]
  }
}
```

## 9. `POST /api/mission-report`  (distance, time, difficulty, resources)
Request: `{ "route": <the Feature returned by /api/route> }`
```json
{
  "distanceKm": 12.4,
  "travelTimeHours": 3.5,
  "difficulty": "Moderate",
  "resources": { "powerKwh": 8.2, "fuelKg": 1.4, "waterL": 3.0 },
  "summary": "Free-text mission summary shown in the report.",
  "generatedAt": "2026-11-06T10:00:00Z"
}
```

---

### Frontend behaviour to be aware of
- On load the app requests hazard-grid, elevation-grid, composition, mineral-ratio, weather and radiation in parallel.
- Route planning fires once the user has clicked START then END (map or 3D terrain); then `elevation-profile` runs. "Generate Report" is disabled until a route exists and calls `mission-report` when clicked.
- Retries: 2 retries with backoff on network errors / 5xx. 4xx responses are not retried.

## Jezero 20 m endpoints (added)
- `GET /api/jezero/config` -> defaults, assumption labels, SPE constants + basis, baseline dose.
- `POST /api/jezero/route` body `{points:[{lat,lon,id,stay_min}], shelter:{lat,lon}, spe:{active,multiplier}, params:{...}}` -> `{fast, safe, spe, assumptions, resolution_label}`; each route has coordinates `[lon,lat,elev]`, metrics, per-waypoint dose / return time / green-amber-red status, consumables.
- `GET /api/jezero/pov?lat&lon&radius_m` -> local 20 m DEM patch (heights in metres) for the synthetic first-person view.
