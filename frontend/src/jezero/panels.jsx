import { useEffect, useState } from 'react'
import { useJez } from './store.js'
import { CRISM_NOTE, LAYERS, PARAM_FIELDS, unitColor } from './constants.js'
import { useMarsStore } from '../store/useMarsStore.js'
import { DEFAULT_REGION } from '../config.js'

const f = (v, d = 1) => (v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(d))
const Stat = ({ k, v, u, cls }) => <div className={`stat ${cls ?? ''}`}><span>{k}</span><b>{v}{u ? <i> {u}</i> : null}</b></div>

export function MissionBrief() {
  const s = useJez(); const r = s.route && !s.route.error ? s.route[s.activeRoute] : null; const sc = s.scenario
  const setRegion = useMarsStore((state) => state.setRegion)
  return (
    <section className="jz-card">
      <div className="mission-heading"><h3>Mission brief</h3><button type="button" className="jz-back-map" onClick={() => setRegion(DEFAULT_REGION)}>← Mars map</button></div>
      <div className="jz-seg"><button className={s.mode === 'scenario' ? 'on' : ''} onClick={() => s.setMode('scenario')}>2-person EVA scenario</button><button className={s.mode === 'custom' ? 'on' : ''} onClick={() => s.setMode('custom')}>Custom 2-point</button></div>
      <p className="dim">{s.mode === 'scenario' ? `${sc?.scenario?.name}: ${sc?.start?.name} → selected delta-front target(s). Shelter / start: landing site.` : 'Click the map for START then END.'}</p>
      <div className="stats">
        <Stat k="Crew" v={s.params.crew ?? 2} /><Stat k="Distance" v={r ? f(r.distance_km, 2) : '—'} u="km" /><Stat k="EVA duration" v={r ? f(r.total_eva_h, 1) : '—'} u="h (walk+stay+return)" />
        <Stat k="O₂" v={r ? f(r.consumables.o2_kg, 1) : '—'} u="kg*" /><Stat k="Water" v={r ? f(r.consumables.water_kg, 1) : '—'} u="kg*" /><Stat k="Power" v={r ? f(r.consumables.power_kwh, 1) : '—'} u="kWh*" />
      </div>
      <small className="dim">*Consumables = ASSUMED rates × crew × EVA hours × (1+reserve). Edit constants below.</small>
      <details><summary>Editable constants (assumptions)</summary>
        {PARAM_FIELDS.map(([k, label, unit]) => (
          <label key={k} className="param"><span>{label} <i>{unit}</i></span><input type="number" step="any" value={s.params[k] ?? ''} onChange={(e) => s.setParam(k, e.target.value)} /><em>{s.config?.assumption_labels?.[k] ?? ''}</em></label>
        ))}
        <p className="dim">Shelter: {s.shelter?.name ?? 'landing site'} ({f(s.shelter?.lat, 4)}°N, {f(s.shelter?.lon, 4)}°E). Baseline dose {s.config?.baseline?.msv_per_hour ?? 0.027} mSv/h ({s.config?.baseline?.msv_per_sol ?? 0.67} mSv/sol, existing RadiationService).</p>
      </details>
      <button className="jz-go" disabled={s.routeStatus === 'loading' || !s.config} onClick={s.calculate}>{s.routeStatus === 'loading' ? 'Calculating…' : 'Calculate'}</button>
      {s.backendError && <p className="err">Backend: {s.backendError}</p>}
      {s.route?.error && <p className="err">{s.route.detail}</p>}
    </section>
  )
}

export function Targets() {
  const s = useJez()
  return (
    <section className="jz-card">
      <h3>Science targets <small>Stack et al. 2020, Table 2</small></h3>
      {s.targets.map((t) => (
        <div key={t.id} className={`tgt ${s.selected.includes(t.id) ? 'on' : ''}`}>
          <label><input type="checkbox" checked={s.selected.includes(t.id)} disabled={s.mode !== 'scenario'} onChange={() => s.toggleTarget(t.id)} /> <b>{t.id}</b> {t.name}{s.selected.includes(t.id) && <em> #{s.selected.indexOf(t.id) + 1}</em>}</label>
          <div className="tgt-row"><span>{t.lat.toFixed(3)}°N {t.lon.toFixed(3)}°E · {t.crism_class ?? 'no CRISM'}{t.crism_distance_m != null ? ` (${t.crism_distance_m} m)` : ''}</span>
            <label>stay <input type="number" min="0" value={t.stay_min} onChange={(e) => s.setStay(t.id, e.target.value)} /> min*</label><button onClick={() => s.openGallery(t.id)}>info</button></div>
        </div>
      ))}
      <small className="dim">Route visits selected targets in the order ticked. *Stay time is an ASSUMPTION. CRISM class = nearest identified 36 m pixel; {CRISM_NOTE}.</small>
    </section>
  )
}

export function LayerPanel() {
  const s = useJez(); const [open, setOpen] = useState(null)
  return (
    <section className="jz-card">
      <h3>Layers</h3>
      {LAYERS.map((l) => {
        const st = s.layers[l.id]
        return (
          <div key={l.id} className="lyr">
            <label><input type="checkbox" checked={st.on} onChange={(e) => s.setLayer(l.id, { on: e.target.checked })} /> {l.label}</label>
            <input type="range" min="0.1" max="1" step="0.05" value={st.op} onChange={(e) => s.setLayer(l.id, { op: Number(e.target.value) })} aria-label={`${l.label} opacity`} />
            <button className="lnk" onClick={() => setOpen(open === l.id ? null : l.id)}>{open === l.id ? '▾' : '▸'}</button>
            {open === l.id && <Legend l={l} />}
          </div>
        )
      })}
    </section>
  )
}

function Legend({ l }) {
  const s = useJez(); const [units, setUnits] = useState([])
  useEffect(() => { if (l.legend?.units) fetch('/jezero/geology_units.geojson').then((r) => r.json()).then((g) => setUnits([...new Set(g.features.map((x) => x.properties[l.field]).filter(Boolean))].sort())) }, [l])
  return (
    <div className="legend"><small>Source: {l.source}</small>
      {l.legend?.ramp && <><div className="ramp" style={{ background: l.legend.ramp }} /><div className="ramp-l"><span>{l.legend.min}</span><span>{l.legend.unit}</span><span>{l.legend.max}</span></div></>}
      {l.legend?.note && <small>{l.legend.note}</small>}
      {l.legend?.classes && <><small>{CRISM_NOTE}. Bold = high confidence, dark = medium; black = unidentified (transparent).</small>
        {s.manifest?.crism?.classes.map((c) => <div key={c.name} className="sw"><i style={{ background: `rgb(${c.high_conf_rgb})` }} /><i style={{ background: `rgb(${c.medium_conf_rgb})` }} /> {c.name}</div>)}</>}
      {l.legend?.units && units.map((u) => <label key={u} className="sw"><input type="checkbox" checked={!s.hiddenUnits[`${l.id}:${u}`]} onChange={() => s.toggleUnit(`${l.id}:${u}`)} /><i style={{ background: unitColor(u) }} /> {u}</label>)}
    </div>
  )
}

const ST = { green: '#3ddc97', amber: '#ffb000', red: '#ff4d5a' }
export function RoutePanel() {
  const s = useJez(); const ok = s.route && !s.route.error; const r = ok ? s.route[s.activeRoute] : null; const o = ok ? s.route[s.activeRoute === 'fast' ? 'safe' : 'fast'] : null
  if (!r) return <section className="jz-card"><h3>Route</h3><p className="dim">Press Calculate. Routing uses slope-limited cost-based A* on the 20 m CTX terrain.</p></section>
  const dd = s.route.safe.dose_total_msv - s.route.fast.dose_total_msv; const dk = s.route.safe.distance_km - s.route.fast.distance_km
  return (
    <section className="jz-card">
      <h3>Route <small>{s.route.resolution_label} · grid {s.route.grid_step_m} m</small></h3>
      <div className="jz-seg"><button className={s.activeRoute === 'fast' ? 'on' : ''} onClick={() => s.setActiveRoute('fast')}>Fastest</button><button className={s.activeRoute === 'safe' ? 'on' : ''} onClick={() => s.setActiveRoute('safe')}>Safer (shielding)</button></div>
      <div className="stats">
        <Stat k="Distance" v={f(r.distance_km, 2)} u="km" /><Stat k="Climb / descent" v={`${r.climb_m} / ${r.descent_m}`} u="m" /><Stat k="Walk time" v={f(r.walk_time_h, 2)} u="h" />
        <Stat k="Max / mean slope" v={`${r.max_slope_deg} / ${r.mean_slope_deg}`} u="°" /><Stat k="Difficulty" v={f(r.difficulty_0_10, 1)} u="/ 10" /><Stat k="Dose (round trip)" v={f(r.dose_total_msv, 3)} u="mSv" />
      </div>
      <small className="dim">{r.difficulty_formula}</small>
      <p className="cmp">Safer vs fastest: {dk >= 0 ? '+' : ''}{f(dk, 2)} km, {dd >= 0 ? '+' : ''}{f(dd, 4)} mSv. {Math.abs(dd) < 0.003 ? 'Terrain shielding (assumed mapping) gives no meaningful difference on this corridor.' : dd < 0 ? 'Safer route reduces assumed dose.' : 'No dose benefit.'}</p>
      {o && <small className="dim">Dashed line = the other route.</small>}
    </section>
  )
}

export function RadiationPanel() {
  const s = useJez(); const [now, setNow] = useState(Date.now()); useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t) }, [])
  const r = s.route && !s.route.error ? s.route[s.activeRoute] : null; const el = s.spe.active ? Math.floor((now - s.spe.startedAt) / 1000) : 0
  const mm = String(Math.floor(el / 60)).padStart(2, '0'), ss = String(el % 60).padStart(2, '0')
  const worst = r?.worst_status
  return (
    <section className={`jz-card ${s.spe.active ? 'spe' : ''}`}>
      <h3>Radiation & SPE</h3>
      {s.spe.active && <div className="banner">SIMULATED EVENT · SPE ×{s.spe.multiplier.toFixed(1)} · T+{mm}:{ss} · severity {s.spe.multiplier >= 3 ? 'WORST CASE' : 'NOMINAL'}</div>}
      <div className="jz-seg"><button onClick={() => s.startSpe(2)} className={s.spe.active && s.spe.multiplier === 2 ? 'on' : ''}>Simulate SPE ×2.0</button><button onClick={() => s.startSpe(3)} className={s.spe.active && s.spe.multiplier === 3 ? 'on' : ''}>Worst ×3.0</button><button onClick={s.endSpe}>Clear</button></div>
      <small className="dim">{s.config?.spe?.basis}. Baseline {s.config?.baseline?.msv_per_hour} mSv/h. Press Calculate after changing the event. Shielding factors are ASSUMPTIONS (editable), not measured data.</small>
      {worst === 'red' && <div className="banner red">RETURN NOW: dose budget would be exceeded by the time you reach shelter</div>}
      {r && <table className="wp"><thead><tr><th>Waypoint</th><th>Dose</th><th>Home</th><th>Margin</th><th /></tr></thead><tbody>
        {r.waypoints.map((w, i) => <tr key={i} onClick={() => s.setSelWp(i)}><td>{r.names?.[i] ?? w.id}</td><td>{f(w.dose_msv, 3)}</td><td>{f(w.return_time_h, 2)} h</td><td>{f(w.dose_margin_msv, 3)}</td><td style={{ color: ST[w.status] }}>● {w.instruction}</td></tr>)}
      </tbody></table>}
      {r && <small className="dim">Dose in mSv (cumulative incl. stays). Home = walking time back to shelter. Margin = budget − (dose so far + dose on the way home).</small>}
    </section>
  )
}

export function GalleryCard() {
  const s = useJez(); const t = s.targets.find((x) => x.id === s.galleryTarget); const [big, setBig] = useState(null)
  if (!t) return null
  return (
    <div className="jz-modal" onClick={() => { s.openGallery(null); setBig(null) }}>
      <div className="jz-card jz-modal-in" onClick={(e) => e.stopPropagation()}>
        <h3>{t.id} · {t.name}</h3>
        <p><b>Unit:</b> {t.description}</p><p><b>Interpretation:</b> {t.interpretation}</p>
        <p className="dim">Type location {t.lat}°N, {t.lon}°E · elevation {f(t.dem_elev_m, 0)} m (20 m CTX DEM) · nearest CRISM class: {t.crism_class ?? 'none'} ({CRISM_NOTE}). Source: Stack et al. 2020, Table 2.</p>
        <h4>{s.gallery?.title}</h4><p className="warn">{s.gallery?.note} They are shown here for context only and are not the view at {t.id}.</p>
        <div className="gal">{s.gallery?.items.map((g) => <figure key={g.id} onClick={() => setBig(g)}><img src={g.thumb} alt={`${g.camera} ${g.product} sol ${g.sol}`} loading="lazy" /><figcaption>{g.camera}<br />{g.product} · sol {g.sol}</figcaption></figure>)}</div>
        {big && <img className="gal-big" src={big.file} alt={`${big.camera} sol ${big.sol}`} />}
        <button className="jz-go" onClick={() => { s.openGallery(null); setBig(null) }}>Close</button>
      </div>
    </div>
  )
}
