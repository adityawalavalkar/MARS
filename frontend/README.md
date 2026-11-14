# MARS NAV — frontend

Vite + React 19 · three / react-three-fiber / drei · framer-motion · Leaflet · zustand · plain CSS.

## Run
```bash
npm install
cp .env.example .env     # then edit VITE_API_BASE_URL
npm run dev              # http://localhost:5173
npm run build            # production build -> dist/
npm run lint             # oxlint
```
Install commands used to create this project:
```bash
npm install three @react-three/fiber @react-three/drei framer-motion leaflet react-leaflet zustand react react-dom
npm install -D vite @vitejs/plugin-react oxlint
```

## Backend connection
- **Base URL:** `VITE_API_BASE_URL` in `.env` (see `.env.example`).
- **Endpoint paths:** the single `endpoints` object at the top of `src/services/api.js`.
- **Shapes / units:** `FRONTEND_API_CONTRACT.md`.
- There is **no mock data**. Until the backend answers, cards show "—" / "No data yet"; failures show "Data unavailable". Machine Settings -> *Backend connection* shows per-endpoint status.

## HiRISE imagery (2D map)
Paste the WMTS template from `documentation/hirise_source.txt` into `VITE_HIRISE_TILE_URL` (or `HIRISE_TILE_URL` in `src/config.js`). `{TileMatrix}/{TileRow}/{TileCol}` and `{z}/{y}/{x}` placeholders are both supported; the map uses EPSG:4326. Without it (or if tiles fail) the map shows a dark-orange fallback and still draws heat layers and routes.

## Mars texture
`public/textures/mars.jpg` (2:1 equirectangular). To swap it, replace the file or change `MARS_TEXTURE_URL` in `src/config.js`.

## Change the region
`DEFAULT_REGION` in `src/config.js` (`name`, `zone` title, `center`, `bounds`). Requests, map fit and the 3D mesh all follow it.

## Notes
- Intro plays once per session (`sessionStorage` key `marsnav:intro-seen`); "Skip intro" is top-right.
- Tabs: Overview · Hazard Map (2D + hazard layer) · Mission Planner (2D) · Machine Settings.
- Click the map/terrain to set START, then END, then again to restart.
