import { CTX_TILE_URL, HIRISE_TILE_URL, THEMIS_DAY_TILE_URL, THEMIS_NIGHT_TILE_URL } from '../config.js'
export const tpl = (u) => u.replaceAll('{TileMatrix}', '{z}').replaceAll('{TileRow}', '{y}').replaceAll('{TileCol}', '{x}')
export const unitColor = (name) => { let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360; return `hsl(${h} 65% 55%)` }
const VIRIDIS = 'linear-gradient(90deg,#440154,#3b528b,#21918c,#5ec962,#fde725)'
const HAZ = 'linear-gradient(90deg,#ffffcc,#fed976,#fd8d3c,#e31a1c,#800026)'
// kind: tile | image | geo ; every layer carries a source label and a legend spec
export const LAYERS = [
  { id: 'hirise', label: 'HiRISE 25 cm', kind: 'tile', url: tpl(HIRISE_TILE_URL), maxNative: 17, source: 'NASA Trek / MRO HiRISE orthomosaic 25 cm/px', on: false, op: 1 },
  { id: 'ctx', label: 'CTX 6 m', kind: 'tile', url: tpl(CTX_TILE_URL), maxNative: 13, source: 'NASA Trek / MRO CTX orthomosaic 6 m/px', on: true, op: 1 },
  { id: 'themisDay', label: 'THEMIS day IR', kind: 'tile', url: tpl(THEMIS_DAY_TILE_URL), maxNative: 8, source: 'NASA Trek / Odyssey THEMIS day IR 100 m/px', on: false, op: 0.8 },
  { id: 'themisNight', label: 'THEMIS night IR', kind: 'tile', url: tpl(THEMIS_NIGHT_TILE_URL), maxNative: 8, source: 'NASA Trek / Odyssey THEMIS night IR 100 m/px', on: false, op: 0.8 },
  { id: 'ti', label: 'Thermal inertia', kind: 'image', src: '/jezero/thermal_inertia.png', bounds: 'thermal_inertia', source: 'Jezero_Thermal_Inertia_v1.tiff, 100 m', on: false, op: 0.75, legend: { ramp: VIRIDIS, min: '42', max: '600+', unit: 'J m-2 K-1 s-0.5', note: 'Display only; not used for rock or hazard.' } },
  { id: 'crism', label: 'CRISM minerals', kind: 'image', src: '/jezero/crism_minerals.png', bounds: 'crism', source: 'Preliminary mineral attribution (Parente/Itoh/Saranathan CRISM map), 36 m', on: false, op: 0.85, legend: { classes: true } },
  { id: 'geoSurf', label: 'Geologic units: surface', kind: 'geo', field: 'SurfUName', source: 'Stack et al. 2020 photogeologic map (Mars 2020 Science Team)', on: false, op: 0.55, legend: { units: true } },
  { id: 'geoBed', label: 'Geologic units: bedrock', kind: 'geo', field: 'BedrkUName', source: 'Stack et al. 2020 photogeologic map (Mars 2020 Science Team)', on: false, op: 0.55, legend: { units: true } },
  { id: 'hazard', label: 'Obstacle layer (derived hazard)', kind: 'image', src: '/jezero/hazard.png', bounds: 'dem', source: '20 m CTX DEM slope + roughness + ASSUMED unit costs. Derived hazard, not measured rock abundance.', on: false, op: 0.8, legend: { ramp: HAZ, min: '1 easy', max: '4 hard', unit: 'derived index' } },
  { id: 'hillshade', label: 'Hillshade', kind: 'image', src: '/jezero/hillshade.png', bounds: 'dem', source: '20 m CTX DEM (M20_JezeroCrater_CTXDEM_20m)', on: false, op: 0.6 },
  { id: 'slope', label: 'Slope', kind: 'image', src: '/jezero/slope.png', bounds: 'dem', source: '20 m CTX DEM, Horn slope', on: false, op: 0.7, legend: { ramp: 'linear-gradient(90deg,#000004,#51127c,#b73779,#fc8961,#fcfdbf)', min: '0', max: '30', unit: 'degrees' } },
]
export const CRISM_NOTE = 'preliminary mineral attribution (Parente/Itoh/Saranathan CRISM map)'
export const PARAM_FIELDS = [
  ['walk_speed_kmh', 'Walking speed', 'km/h'], ['slope_limit_deg', 'Suit slope limit', '°'], ['rad_weight', 'Radiation weight (safer route)', ''],
  ['dose_budget_msv', 'EVA dose budget', 'mSv'], ['amber_margin_frac', 'Amber margin', 'fraction of budget'], ['max_shield_reduction', 'Max terrain shielding', 'fraction'],
  ['crew', 'Crew', 'people'], ['o2_kg_per_person_h', 'O₂ per person', 'kg/h'], ['water_kg_per_person_h', 'Water per person', 'kg/h'],
  ['power_w_per_person', 'Power per person', 'W'], ['consumable_reserve_frac', 'Consumables reserve', 'fraction'],
]
