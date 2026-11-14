import { create } from 'zustand'
import { DEFAULT_REGION, POLL_SECONDS } from '../config.js'

// status per data key: 'idle' | 'loading' | 'ready' | 'error'
const KEYS = ['weather', 'radiation', 'hazard', 'elevation', 'composition', 'mineral', 'regional', 'regionalFeatures', 'route', 'profile', 'calculation', 'report']
const empty = (v) => Object.fromEntries(KEYS.map((k) => [k, v]))

export const useMarsStore = create((set, get) => ({
  selectedRegion: DEFAULT_REGION,
  start: null, // { lat, lon }
  end: null,
  activeLayer: 'none',
  layerOpacity: 0.7,
  viewMode: '2d', // Regional overview opens in 2D; Jezero retains 3D on request.
  activeTab: 'overview', // overview | hazard | planner | settings
  settings: { tempUnit: 'C', exaggeration: 1, overlay3d: 'elevation', refreshSeconds: POLL_SECONDS },
  appPhase: 'MAP', // INTRO → MAP → REGION_LOADING → REGION_3D → POINTS_SELECTED → RESULTS
  calculationRequested: false,
  data: empty(null),
  status: empty('idle'),
  lastUpdated: null, // ms timestamp of last successful weather/radiation fetch
  reportOpen: false,
  missionMode: 'rover',
  safetyWeight: 1.5,
  crewSize: 2,
  roverSpeedKmh: 0.042,

  setAppPhase: (appPhase) => set({ appPhase }),
  setRegion: (region) => set({ selectedRegion: region, appPhase: region.id === 'regional' ? 'MAP' : 'REGION_LOADING', viewMode: '2d', start: null, end: null, calculationRequested: false, data: empty(null), status: empty('idle'), lastUpdated: null }),

  // Click flow: 1st click = START, 2nd = END, 3rd restarts with a new START.
  pickPoint: (lat, lon) => {
    const { start, end } = get()
    if (!start || (start && end)) set({ start: { lat, lon }, end: null, calculationRequested: false, appPhase: 'POINTS_SELECTED', data: { ...get().data, route: null, profile: null, calculation: null, report: null } })
    else set({ end: { lat, lon }, appPhase: 'POINTS_SELECTED', calculationRequested: false, data: { ...get().data, route: null, profile: null, calculation: null, report: null } })
  },
  requestCalculation: (calculationRequested = true) => set({ calculationRequested }),
  clearRoute: () =>
    set((s) => ({ start: null, end: null, calculationRequested: false, data: { ...s.data, route: null, profile: null, calculation: null, report: null }, status: { ...s.status, route: 'idle', profile: 'idle', calculation: 'idle', report: 'idle' } })),

  setLayer: (activeLayer) => set({ activeLayer }),
  setOpacity: (layerOpacity) => set({ layerOpacity }),
  setViewMode: (viewMode) => set((s) => ({ viewMode, appPhase: viewMode === '2d' ? 'MAP' : s.selectedRegion.id === 'jezero' ? 'REGION_3D' : s.appPhase })),
  setTab: (activeTab) =>
    set((s) => ({
      activeTab,
      viewMode: activeTab === 'hazard' || activeTab === 'planner' ? '2d' : s.viewMode,
      activeLayer: activeTab === 'hazard' ? 'hazard' : s.activeLayer,
    })),
  updateSettings: (patch) => set((s) => ({ settings: { ...s.settings, ...patch } })),
  setReportOpen: (reportOpen) => set({ reportOpen }),
  setMissionOptions: (patch) => set((s) => ({ ...s, ...patch })),

  setStatus: (key, value) => set((s) => ({ status: { ...s.status, [key]: value } })),
  setResult: (key, value, { touch = false } = {}) =>
    set((s) => ({
      data: { ...s.data, [key]: value },
      status: { ...s.status, [key]: value?.error ? 'error' : value ? 'ready' : 'error' },
      lastUpdated: touch && value ? Date.now() : s.lastUpdated,
    })),
}))
