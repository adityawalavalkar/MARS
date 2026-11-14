// Central configuration for MARS NAV. Edit values here (or via .env).

// Equirectangular Mars colour map used by the intro globe. Swap the file in public/textures/ to change it.
export const MARS_TEXTURE_URL = '/textures/mars.jpg'

// NASA Trek HiRISE Jezero mosaic (retained for optional deep inspection).
export const HIRISE_TILE_URL =
  import.meta.env.VITE_HIRISE_TILE_URL ||
  'https://trek.nasa.gov/tiles/Mars/EQ/JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd/1.0.0/default/default028mm/{TileMatrix}/{TileRow}/{TileCol}.png'
export const HIRISE_MAX_ZOOM = 17
export const HIRISE_NATIVE_MAX_ZOOM = 17
export const HIRISE_COVERAGE = { south: 18.30, west: 77.30, north: 18.52, east: 77.58 }

// Verified by the Trek WMTS GetCapabilities document: JPEG, default style,
// default028mm matrix set, numeric matrix IDs, top-left (-180°, 90°).
export const MOLA_TILE_URL = 'https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{TileMatrix}/{TileRow}/{TileCol}.jpg'

// CTX provides the wider local-exploration imagery requested at Jezero.  Leaflet
// loads only tiles crossing the current viewport and the browser retains nearby
// tiles via the layer's keepBuffer setting.
export const CTX_TILE_URL =
  import.meta.env.VITE_CTX_TILE_URL ||
  'https://trek.nasa.gov/tiles/Mars/EQ/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0/1.0.0/default/default028mm/{TileMatrix}/{TileRow}/{TileCol}.png'
export const CTX_MAX_ZOOM = 13 // highest TileMatrix present in this layer's GetCapabilities
export const LOCAL_EXPLORATION_ZOOM = 10

// Default region of interest. Change `name`, `zone`, `center` and `bounds` to move the whole app.
export const JEZERO_REGION = {
  id: 'jezero',
  name: 'Jezero Crater',
  zone: 'Jezero Zone / Area 1',
  center: { lat: 18.45, lon: 77.55 },
  bounds: { south: 18.2, west: 77.3, north: 18.7, east: 77.8 },
  analysisAvailable: true,
  terrainAvailable: true,
}

// Exact MOLA raster extent returned by /api/terrain/elevation; clicks outside
// these bounds must never trigger a route request.
export const JEZERO_RASTER_BOUNDS = { west: 76.6953124933, south: 17.4062500011, east: 78.6953124934, north: 19.4062500013 }

export const REGIONAL_REGION = {
  id: 'regional',
  name: 'Nili–Isidis Regional Map',
  zone: 'Nili–Isidis Regional Overview',
  center: { lat: 19.5, lon: 77.5 },
  bounds: { south: 12, west: 65, north: 27, east: 90 },
}

// IAU/USGS Gazetteer control points (planetocentric latitude, east longitude).
// The project bundle contains detailed analysis rasters only for Jezero; these
// markers remain selectable but show an explicit data-availability state.
const gazetteer = (id, name, kind, lat, lon, west, south, east, north, source) => ({
  id, name, kind, center: { lat, lon },
  bounds: { west, south, east, north },
  zone: name,
  source: `https://planetarynames.wr.usgs.gov/Feature/${source}`,
  analysisAvailable: id === 'jezero',
  terrainAvailable: id === 'jezero' || (lon >= 65 && lon <= 90 && lat >= 12 && lat <= 27),
})
export const MARS_REGIONS = [
  gazetteer('olympus-mons', 'Olympus Mons', 'Mons', 18.65, 226.20, 220.7, 13.55, 231.0, 23.55, 4453),
  gazetteer('valles-marineris', 'Valles Marineris', 'Vallis', -14.01, 301.41, 267.3, -19.09, 331.1, -2.96, 6288),
  gazetteer('hellas-planitia', 'Hellas Planitia', 'Planitia', -42.43, 70.50, 60, -55, 80, -30, 2432),
  gazetteer('argyre-planitia', 'Argyre Planitia', 'Planitia', -49.67, 316.00, 300, -60, 330, -35, 371),
  gazetteer('tharsis-montes', 'Tharsis Montes', 'Montes', 1.57, 247.42, 237, -11.57, 257.6, 13.45, 5948),
  gazetteer('syrtis-major', 'Syrtis Major Planum', 'Planum', 9.2, 67.1, 59, -0.99, 77, 18.79, 5796),
  gazetteer('arabia-terra', 'Arabia Terra', 'Terra', 21.25, 5.72, 335, -19.78, 50, 44.66, 336),
  gazetteer('utopia-planitia', 'Utopia Planitia', 'Planitia', 46.74, 117.52, 65, 12.92, 164.89, 73.17, 6260),
  gazetteer('elysium-mons', 'Elysium Mons', 'Mons', 25.02, 147.21, 140, 20, 155, 30, 1783),
  gazetteer('gale', 'Gale Crater', 'Crater', -5.44, 137.70, 136.4, -6.62, 138.9, -4.05, 2071),
  { ...JEZERO_REGION, center: { lat: 18.41, lon: 77.69 }, kind: 'Crater', source: 'https://planetarynames.wr.usgs.gov/Feature/14300', analysisAvailable: true, terrainAvailable: true },
  gazetteer('isidis-planitia', 'Isidis Planitia', 'Planitia', 13.94, 88.38, 77, 12, 90, 22.76, 2735),
  gazetteer('chryse-planitia', 'Chryse Planitia', 'Planitia', 28.43, 319.69, 305, 11.86, 335, 37.67, 1203),
]

// The app opens at Level 1. Selecting Jezero retains the full existing local
// hazard, routing, and 3D workflow.
export const MARS_MAP_REGION = {
  id: 'global', name: 'Mars', zone: 'Mars Global Map',
  center: { lat: 22, lon: 45 }, bounds: { south: 0, west: 0, north: 44, east: 90 }, // MOLA 0-90E, 0-44N
}
export const DEFAULT_REGION = MARS_MAP_REGION

export const ELEVATION_RESOLUTION = 256 // matches the bundled 256 × 256 MOLA DEM source raster
export const POLL_SECONDS = 45 // weather + radiation refresh interval
export const SESSION_INTRO_KEY = 'marsnav:intro-seen'

export const COLORS = {
  sand: '#f3d9cc',
  rust: '#c1440e',
  brown: '#2a1410',
  space: '#07050a',
  glow: '#ff7a3d',
  hazard: '#e5484d',
  safe: '#2fbfa5',
}

// ---- Jezero 20 m module (added) ----
// THEMIS IR templates follow the Trek WMTS pattern from DATA/raw/THEMIS/*.txt with the corrected .png tile template.
// NOTE: tile-matrix limits were not verified offline; if tiles 404, check each layer's GetCapabilities.
const TREK = 'https://trek.nasa.gov/tiles/Mars/EQ'
export const THEMIS_DAY_TILE_URL = `${TREK}/THEMIS_DayIR_ControlledMosaics_100m_v2_oct2018/1.0.0/default/default028mm/{TileMatrix}/{TileRow}/{TileCol}.png`
export const THEMIS_NIGHT_TILE_URL = `${TREK}/THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018/1.0.0/default/default028mm/{TileMatrix}/{TileRow}/{TileCol}.png`
export const THEMIS_MAX_ZOOM = 8
export const VERT_EXAG_DEFAULT = 2 // 3D vertical exaggeration (adjustable in the UI)
