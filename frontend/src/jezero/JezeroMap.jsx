import { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import { CircleMarker, GeoJSON, ImageOverlay, MapContainer, Polyline, TileLayer, Tooltip, ZoomControl, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { MOLA_TILE_URL } from '../config.js'
import { useJez } from './store.js'
import { LAYERS, tpl, unitColor } from './constants.js'

const R_MARS = 3396190
const MARS_EQ_CRS = L.extend({}, L.CRS.EPSG4326, { transformation: new L.Transformation(1 / 180, 1, -1 / 180, 0.5), scale: (z) => 256 * 2 ** z, zoom: (s) => Math.log(s / 256) / Math.LN2 })
const STATUS = { green: '#3ddc97', amber: '#ffb000', red: '#ff4d5a' }
const bnd = (b) => [[b[0], b[1]], [b[2], b[3]]]

function Hud({ onMove }) {
  const map = useMap()
  const [scale, setScale] = useState(null)
  useEffect(() => {
    const upd = () => {
      const c = map.getCenter(); const p = map.latLngToContainerPoint(c); const q = map.containerPointToLatLng([p.x + 100, p.y])
      const m = Math.abs(q.lng - c.lng) * (Math.PI / 180) * R_MARS * Math.cos((c.lat * Math.PI) / 180); const nice = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
      const pick = [...nice].reverse().find((n) => n <= m) ?? 10; setScale({ px: (pick / m) * 100, label: pick >= 1000 ? `${pick / 1000} km` : `${pick} m` })
    }
    const mv = (e) => onMove(e.latlng); upd(); map.on('zoomend moveend', upd); map.on('mousemove', mv)
    return () => { map.off('zoomend moveend', upd); map.off('mousemove', mv) }
  }, [map, onMove])
  return scale ? <div className="hud-scale" style={{ width: scale.px }}><span>{scale.label}</span></div> : null
}

function Clicks() {
  const map = useMap(); const mode = useJez((s) => s.mode); const pick = useJez((s) => s.pickCustom)
  useEffect(() => { const f = (e) => mode === 'custom' && pick(e.latlng.lat, e.latlng.lng); map.on('click', f); return () => map.off('click', f) }, [map, mode, pick])
  return null
}

export default function JezeroMap() {
  const manifest = useJez((s) => s.manifest); const layers = useJez((s) => s.layers); const hidden = useJez((s) => s.hiddenUnits)
  const targets = useJez((s) => s.targets); const selected = useJez((s) => s.selected); const scenario = useJez((s) => s.scenario)
  const route = useJez((s) => s.route); const activeRoute = useJez((s) => s.activeRoute); const custom = useJez((s) => s.customPts); const mode = useJez((s) => s.mode)
  const openGallery = useJez((s) => s.openGallery); const toggleTarget = useJez((s) => s.toggleTarget); const setSelWp = useJez((s) => s.setSelWp)
  const [geo, setGeo] = useState(null); const [cursor, setCursor] = useState(null); const readout = useRef(null)
  useEffect(() => { fetch('/jezero/geology_units.geojson').then((r) => r.json()).then(setGeo).catch(() => setGeo(null)) }, [])
  const bounds = manifest?.dem?.bounds_swne
  const hk = JSON.stringify(hidden)
  const geoLayer = (l) => {
    const st = layers[l.id]; if (!st.on || !geo) return null
    return <GeoJSON key={`${l.id}${hk}${st.op}`} data={geo} interactive={false} filter={(f) => f.properties[l.field] && !hidden[`${l.id}:${f.properties[l.field]}`]}
      style={(f) => ({ color: '#0b1218', weight: 0.4, fillColor: unitColor(f.properties[l.field]), fillOpacity: st.op })} />
  }
  const act = route && !route.error ? route[activeRoute] : null
  const other = route && !route.error ? route[activeRoute === 'fast' ? 'safe' : 'fast'] : null
  const line = (r) => r.coordinates.map(([lon, lat]) => [lat, lon])
  const scen = useMemo(() => scenario?.start, [scenario])
  const custPts = mode === 'custom' ? custom : []
  if (!bounds) return <div className="terrain-empty">Loading Jezero layers…</div>
  return (
    <div className="map-wrap jz-map">
      <MapContainer crs={MARS_EQ_CRS} bounds={bnd(bounds)} zoomSnap={0.25} minZoom={7} maxZoom={17} zoomControl={false} attributionControl={false} preferCanvas className="map">
        <TileLayer url={tpl(MOLA_TILE_URL)} maxNativeZoom={9} keepBuffer={3} updateWhenIdle />
        {LAYERS.map((l) => {
          const st = layers[l.id]; if (!st.on) return null
          if (l.kind === 'tile') return <TileLayer key={l.id} url={l.url} maxNativeZoom={l.maxNative} opacity={st.op} keepBuffer={3} updateWhenIdle />
          if (l.kind === 'image') return <ImageOverlay key={l.id} url={l.src} bounds={bnd(manifest[l.bounds].bounds_swne)} opacity={st.op} />
          return geoLayer(l)
        })}
        {other && <Polyline positions={line(other)} pathOptions={{ color: activeRoute === 'fast' ? '#ffb000' : '#00e5ff', weight: 2, dashArray: '6 6', opacity: 0.8 }} interactive={false} />}
        {act && <><Polyline positions={line(act)} pathOptions={{ color: '#000', weight: 8, opacity: 0.35 }} interactive={false} /><Polyline positions={line(act)} pathOptions={{ color: activeRoute === 'fast' ? '#00e5ff' : '#ffb000', weight: 3.5 }} interactive={false} /></>}
        {scen && <CircleMarker center={[scen.lat, scen.lon]} radius={8} pathOptions={{ color: '#fff', fillColor: '#3ddc97', fillOpacity: 1, weight: 2 }}><Tooltip direction="top" permanent>Landing site</Tooltip></CircleMarker>}
        {targets.map((t) => (
          <CircleMarker key={t.id} center={[t.lat, t.lon]} radius={selected.includes(t.id) ? 7 : 5} pathOptions={{ color: '#ffb000', fillColor: selected.includes(t.id) ? '#ffb000' : '#12202b', fillOpacity: 1, weight: 2 }}
            eventHandlers={{ click: () => { openGallery(t.id); if (mode === 'scenario') toggleTarget(t.id) } }}>
            <Tooltip direction="top" permanent={selected.includes(t.id)}>{t.id}</Tooltip>
          </CircleMarker>
        ))}
        {act?.waypoints.map((w, i) => <CircleMarker key={`w${i}`} center={[w.lat, w.lon]} radius={11} pathOptions={{ color: STATUS[w.status], weight: 3, fill: false }} eventHandlers={{ click: () => setSelWp(i) }} />)}
        {custPts.map((p, i) => <CircleMarker key={`c${i}`} center={[p.lat, p.lon]} radius={8} pathOptions={{ color: '#fff', fillColor: i ? '#ff4d5a' : '#3ddc97', fillOpacity: 1, weight: 2 }} />)}
        <Hud onMove={(ll) => { setCursor(ll); if (readout.current) readout.current.textContent = `${ll.lat.toFixed(4)}°N  ${ll.lng.toFixed(4)}°E` }} />
        <Clicks />
        <ZoomControl position="topright" />
      </MapContainer>
      <div className="hud-corners" aria-hidden="true"><i /><i /><i /><i /></div>
      <div className="hud-compass" aria-label="North is up"><b>N</b><span /></div>
      <div className="hud-readout" ref={readout}>{cursor ? '' : 'Hover the map · lat / lon'}</div>
      {mode === 'custom' && <div className="hud-note">Custom mode: click the map for START then END ({custom.length}/2)</div>}
    </div>
  )
}
