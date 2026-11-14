import { create } from 'zustand'
import { LAYERS } from './constants.js'
import { getJezeroConfig, getStatic, planJezero } from './api.js'
import { VERT_EXAG_DEFAULT } from '../config.js'

export const useJez = create((set, get) => ({
  ready: false, manifest: null, scenario: null, config: null, gallery: null, backendError: null,
  mode: 'scenario', selected: ['D-bl'], targets: [], customPts: [],
  layers: Object.fromEntries(LAYERS.map((l) => [l.id, { on: l.on, op: l.op }])), hiddenUnits: {},
  params: {}, shelter: null, spe: { active: false, multiplier: 2, startedAt: null },
  route: null, routeStatus: 'idle', activeRoute: 'fast', view: '2d', exag: VERT_EXAG_DEFAULT, selWp: 0, galleryTarget: null,

  init: async () => {
    const [manifest, scenario, gallery, config] = await Promise.all([getStatic('/jezero/manifest.json'), getStatic('/jezero/science_targets.json'), getStatic('/perseverance/gallery.json'), getJezeroConfig()])
    set({ manifest, scenario, gallery, targets: scenario?.targets ?? [], shelter: scenario ? { lat: scenario.start.lat, lon: scenario.start.lon, name: scenario.start.name } : null,
      config: config?.error ? null : config, backendError: config?.error ? config.detail : null, params: config?.defaults ?? {}, ready: true })
  },
  setMode: (mode) => set({ mode, route: null, routeStatus: 'idle', customPts: [] }),
  toggleTarget: (id) => set((s) => ({ selected: s.selected.includes(id) ? s.selected.filter((x) => x !== id) : [...s.selected, id], route: null, routeStatus: 'idle' })),
  setStay: (id, v) => set((s) => ({ targets: s.targets.map((t) => (t.id === id ? { ...t, stay_min: Math.max(0, Number(v) || 0) } : t)) })),
  setLayer: (id, patch) => set((s) => ({ layers: { ...s.layers, [id]: { ...s.layers[id], ...patch } } })),
  toggleUnit: (k) => set((s) => ({ hiddenUnits: { ...s.hiddenUnits, [k]: !s.hiddenUnits[k] } })),
  setParam: (k, v) => set((s) => ({ params: { ...s.params, [k]: Number(v) } })),
  setShelter: (shelter) => set({ shelter }),
  pickCustom: (lat, lon) => set((s) => ({ customPts: s.customPts.length >= 2 ? [{ lat, lon }] : [...s.customPts, { lat, lon }], route: null, routeStatus: 'idle' })),
  startSpe: (multiplier) => set({ spe: { active: true, multiplier, startedAt: Date.now() } }),
  endSpe: () => set({ spe: { active: false, multiplier: 2, startedAt: null } }),
  setView: (view) => set({ view }), setExag: (exag) => set({ exag }), setActiveRoute: (activeRoute) => set({ activeRoute }),
  setSelWp: (selWp) => set({ selWp }), openGallery: (galleryTarget) => set({ galleryTarget }),

  routePoints: () => {
    const s = get()
    if (s.mode === 'custom') return s.customPts.map((p, i) => ({ ...p, id: i ? 'end' : 'start', stay_min: 0 }))
    if (!s.scenario) return []
    const t = Object.fromEntries(s.targets.map((x) => [x.id, x]))
    return [{ lat: s.scenario.start.lat, lon: s.scenario.start.lon, id: 'landing', name: s.scenario.start.name, stay_min: 0 }, ...s.selected.map((id) => ({ lat: t[id].lat, lon: t[id].lon, id, name: t[id].name, stay_min: t[id].stay_min }))]
  },
  calculate: async () => {
    const s = get(); const points = s.routePoints()
    if (points.length < 2) return set({ route: { error: true, detail: 'Pick at least a start and a destination' }, routeStatus: 'error' })
    set({ routeStatus: 'loading' })
    const r = await planJezero({ points, shelter: s.shelter, spe: s.spe, params: s.params })
    if (!r.error) { r.fast.names = points.map((p) => p.name || p.id); r.safe.names = r.fast.names }
    set({ route: r, routeStatus: r.error ? 'error' : 'ready', selWp: 0 })
  },
}))
