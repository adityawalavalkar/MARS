import { useCallback, useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, ZoomControl, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useMarsStore } from '../../store/useMarsStore.js'
import { CTX_MAX_ZOOM, CTX_TILE_URL, HIRISE_COVERAGE, HIRISE_MAX_ZOOM, HIRISE_NATIVE_MAX_ZOOM, HIRISE_TILE_URL, JEZERO_REGION, JEZERO_RASTER_BOUNDS, LOCAL_EXPLORATION_ZOOM, MARS_REGIONS, MOLA_TILE_URL } from '../../config.js'
import { getRegionalGrid } from '../../services/api.js'
import { getLayerGrid, layerById } from '../../utils/layers.js'
import { sampleAtLatLon } from '../../utils/grid.js'
import { fmt, fmtCoord } from '../../utils/format.js'
import HeatLayer from './HeatLayer.jsx'
import NomenclatureLayer from '../../jezero/NomenclatureLayer.jsx'

const tileTemplate = CTX_TILE_URL.replaceAll('{TileMatrix}', '{z}').replaceAll('{TileRow}', '{y}').replaceAll('{TileCol}', '{x}')
const molaTemplate = MOLA_TILE_URL.replaceAll('{TileMatrix}', '{z}').replaceAll('{TileRow}', '{y}').replaceAll('{TileCol}', '{x}')
const hiriseTemplate = HIRISE_TILE_URL.replaceAll('{TileMatrix}', '{z}').replaceAll('{TileRow}', '{y}').replaceAll('{TileCol}', '{x}')
// Trek's default028mm matrix has 2^(z+1) columns × 2^z rows. Leaflet's
// stock EPSG:4326 CRS doubles the vertical world; this CRS aligns tile edges
// with the WMTS matrix's (-180°, 90°) top-left corner.
const MARS_EQ_CRS = L.extend({}, L.CRS.EPSG4326, {
  transformation: new L.Transformation(1 / 180, 1, -1 / 180, 0.5),
  scale: (zoom) => 256 * 2 ** zoom,
  zoom: (scale) => Math.log(scale / 256) / Math.LN2,
})
const overlaps = (a, b) => a.west <= b.east && a.east >= b.west && a.south <= b.north && a.north >= b.south
const mapLon = (lon) => lon > 180 ? lon - 360 : lon

function FitRegion({ bounds }) {
  const map = useMap()
  useEffect(() => {
    map.fitBounds([[bounds.south, bounds.west], [bounds.north, bounds.east]], { padding: [30, 30] })
  }, [map, bounds])
  return null
}

function RegionalViewportLoader({ onViewChange }) {
  const map = useMap()
  const region = useMarsStore((s) => s.selectedRegion)
  const requestId = useRef(0)
  const timer = useRef(null)

  useEffect(() => {
    const update = () => {
      const b = map.getBounds()
      const viewport = { zoom: map.getZoom(), bounds: { south: b.getSouth(), west: b.getWest(), north: b.getNorth(), east: b.getEast() } }
      onViewChange(viewport)
      if (region.id !== 'regional') return
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(async () => {
        const id = ++requestId.current
        const { setStatus, setResult } = useMarsStore.getState()
        setStatus('regional', 'loading')
        const result = await getRegionalGrid(viewport.bounds, viewport.zoom < 7 ? 192 : 320)
        if (id === requestId.current) setResult('regional', result)
      }, 180)
    }
    update()
    map.on('moveend zoomend', update)
    return () => {
      window.clearTimeout(timer.current)
      map.off('moveend zoomend', update)
    }
  }, [map, onViewChange, region.id])
  return null
}

function Interactions({ readout, displayGrid }) {
  const pickPoint = useMarsStore((s) => s.pickPoint)
  const region = useMarsStore((s) => s.selectedRegion)
  const map = useMap()
  useEffect(() => {
    const onClick = (e) => {
      const { lat, lng } = e.latlng
      if (region.id === 'jezero' && lat >= JEZERO_RASTER_BOUNDS.south && lat <= JEZERO_RASTER_BOUNDS.north && lng >= JEZERO_RASTER_BOUNDS.west && lng <= JEZERO_RASTER_BOUNDS.east) pickPoint(lat, lng)
    }
    const onMove = (e) => {
      if (!readout.current) return
      const { lat, lng } = e.latlng
      const elev = sampleAtLatLon(displayGrid, lat, lng, region.bounds)
      const slope = region.id === 'jezero' ? sampleAtLatLon(useMarsStore.getState().data.elevation?.slope, lat, lng, region.bounds) : null
      readout.current.textContent = `${fmtCoord(lat, lng)}\nelev ${fmt(elev)} m${region.id === 'jezero' ? ` · slope ${fmt(slope, 1)}°` : ''}`
    }
    map.on('click', onClick)
    map.on('mousemove', onMove)
    return () => {
      map.off('click', onClick)
      map.off('mousemove', onMove)
    }
  }, [displayGrid, map, pickPoint, readout, region])
  return null
}

function GazetteerFeatures({ zoom }) {
  const setRegion = useMarsStore((s) => s.setRegion)
  const map = useMap()
  const [visibleLabels, setVisibleLabels] = useState(new Set())
  const [hovered, setHovered] = useState(null)
  useEffect(() => {
    const update = () => {
      const used = []
      const next = new Set()
      for (const feature of MARS_REGIONS) {
        const major = ['jezero', 'gale', 'olympus-mons', 'valles-marineris', 'hellas-planitia', 'syrtis-major'].includes(feature.id)
        if (zoom < 4.5 && !major) continue
        const p = map.latLngToContainerPoint([feature.center.lat, mapLon(feature.center.lon)])
        if (used.some(([x, y]) => Math.hypot(p.x - x, p.y - y) < (zoom < 4.5 ? 80 : 54))) continue
        used.push([p.x, p.y]); next.add(feature.id)
      }
      setVisibleLabels(next)
    }
    update(); map.on('moveend zoomend', update)
    return () => map.off('moveend zoomend', update)
  }, [map, zoom])
  return (
    <>
      {MARS_REGIONS.map((feature) => {
        const jezero = feature.id === 'jezero'
        const label = visibleLabels.has(feature.id)
        return (
          <CircleMarker
            key={feature.id}
            center={[feature.center.lat, mapLon(feature.center.lon)]}
            radius={hovered === feature.id ? 8 : 5}
            pathOptions={{ color: hovered === feature.id ? '#fff' : jezero ? '#ff7a3d' : '#f3d9cc', weight: 2, fillColor: jezero ? '#ff7a3d' : '#e3ad76', fillOpacity: hovered === feature.id ? 0.95 : 0.78 }}
            eventHandlers={{ mouseover: () => setHovered(feature.id), mouseout: () => setHovered(null), click: () => setRegion(jezero ? JEZERO_REGION : { ...feature, center: { ...feature.center, lon: mapLon(feature.center.lon) }, bounds: { ...feature.bounds, west: mapLon(feature.bounds.west), east: mapLon(feature.bounds.east) } }) }}
          >
            <Tooltip key={label ? 'label' : 'hover'} permanent={label} direction="top" className={`region-label ${zoom < 4.5 ? 'region-label-global' : ''} ${jezero ? 'region-label-jezero' : ''}`}>
              <b>{feature.name}</b>{!label && <><br />{feature.kind} · {feature.center.lat.toFixed(2)}°, {feature.center.lon.toFixed(2)}°E</>}
            </Tooltip>
          </CircleMarker>
        )
      })}
    </>
  )
}

export default function Map2D() {
  const region = useMarsStore((s) => s.selectedRegion)
  const start = useMarsStore((s) => s.start)
  const end = useMarsStore((s) => s.end)
  const route = useMarsStore((s) => s.data.route)
  const data = useMarsStore((s) => s.data)
  const activeLayer = useMarsStore((s) => s.activeLayer)
  const elevationStatus = useMarsStore((s) => s.status.elevation)
  const opacity = useMarsStore((s) => s.layerOpacity)
  const readout = useRef(null)
  const [viewport, setViewport] = useState({ zoom: 5, bounds: region.bounds })
  const [tiles, setTiles] = useState({ errors: 0, loaded: false })
  const onViewChange = useCallback((next) => setViewport(next), [])

  const regionalMode = region.id === 'regional'
  const layer = layerById(activeLayer)
  const grid = regionalMode ? data.regional?.grid : getLayerGrid(activeLayer, data)
  const line = route ? route.coordinates.map(([lon, lat]) => [lat, lon]) : null
  const localExploration = viewport.zoom >= LOCAL_EXPLORATION_ZOOM && overlaps(viewport.bounds, JEZERO_REGION.bounds)
  const hiriseVisible = viewport.zoom >= 12 && overlaps(viewport.bounds, HIRISE_COVERAGE)
  const tilesFailed = CTX_TILE_URL && tiles.errors > 3 && !tiles.loaded

  return (
    <div className="map-wrap">
      <MapContainer crs={MARS_EQ_CRS} center={[region.center.lat, region.center.lon]} zoom={region.id === 'global' ? 1 : 5} zoomSnap={0.25} minZoom={0} maxZoom={HIRISE_MAX_ZOOM} zoomControl={false} className="map" attributionControl={false}>
        <FitRegion bounds={region.bounds} />
        <RegionalViewportLoader onViewChange={onViewChange} />
        <TileLayer url={molaTemplate} maxNativeZoom={17} keepBuffer={3} updateWhenIdle />
        {localExploration && CTX_TILE_URL && <TileLayer url={tileTemplate} maxNativeZoom={CTX_MAX_ZOOM} keepBuffer={4} updateWhenIdle eventHandlers={{ tileerror: () => setTiles((t) => ({ ...t, errors: t.errors + 1 })), tileload: () => setTiles((t) => (t.loaded ? t : { ...t, loaded: true })) }} />}
        {hiriseVisible && <TileLayer url={hiriseTemplate} maxNativeZoom={HIRISE_NATIVE_MAX_ZOOM} keepBuffer={2} updateWhenIdle />}
        {activeLayer !== 'none' && <HeatLayer grid={grid} layer={layer} opacity={opacity} fallbackBounds={region.bounds} />}
        {region.id === 'global' ? <NomenclatureLayer zoom={viewport.zoom} /> : <GazetteerFeatures zoom={viewport.zoom} />}
        {line && <><Polyline positions={line} pathOptions={{ color: '#ff7a3d', weight: 12, opacity: 0.22, lineCap: 'round' }} interactive={false} /><Polyline positions={line} pathOptions={{ color: '#fff1e0', weight: 3, opacity: 0.95, lineCap: 'round' }} interactive={false} /></>}
        {route?.comparison?.map((candidate) => <Polyline key={candidate.label} positions={candidate.coordinates.map(([lon, lat]) => [lat, lon])} pathOptions={{ color: candidate.label === 'Fast' ? '#f9c74f' : '#43aa8b', weight: 2, opacity: 0.85, dashArray: '6 6' }} interactive={false} />)}
        {route?.waypoints.map((w, i) => <CircleMarker key={i} center={[w.lat, w.lon]} radius={4} pathOptions={{ color: '#fff1e0', fillColor: '#ff7a3d', fillOpacity: 1, weight: 1.5 }} interactive={false} />)}
        {start && <CircleMarker center={[start.lat, start.lon]} radius={8} pathOptions={{ color: '#fff', fillColor: '#2fbfa5', fillOpacity: 1, weight: 2 }} />}
        {end && <CircleMarker center={[end.lat, end.lon]} radius={8} pathOptions={{ color: '#fff', fillColor: '#e5484d', fillOpacity: 1, weight: 2 }} />}
        <Interactions readout={readout} displayGrid={grid} />
        <ZoomControl position="topright" />
      </MapContainer>
      {localExploration && (!CTX_TILE_URL || tilesFailed) && <div className="map-note">CTX imagery unavailable — regional MOLA overview remains active</div>}
      {region.id !== 'global' && region.id !== 'regional' && !region.terrainAvailable && <div className="map-note map-note-low">{region.name}: no local MOLA elevation DEM is bundled for this location. Select Isidis or Jezero for included terrain data.</div>}
      {region.id !== 'global' && region.id !== 'regional' && region.terrainAvailable && region.id !== 'jezero' && <div className="map-note map-note-low">{region.name}: regional MOLA overview only; hazards, route planning, and rover-scale analysis are unavailable at this resolution.</div>}
      {region.id === 'jezero' && elevationStatus === 'loading' && <div className="map-note map-note-low">Loading the 256 × 256 MOLA Jezero elevation grid…</div>}
      {region.id === 'jezero' && elevationStatus === 'error' && <div className="map-note map-note-low">Jezero DEM unavailable. Verify the backend and local raster, then retry by selecting Jezero again.</div>}
      {activeLayer !== 'none' && !grid && <div className="map-note map-note-low">Loading {regionalMode ? 'regional MOLA overview' : layer.label.toLowerCase()}…</div>}
      <div className="map-readout" ref={readout}>Hover the map for coordinates</div>
      <div className="map-attribution">Imagery: NASA/JPL/USGS MOLA (463 m/px), CTX (6 m/px), HiRISE (~0.25 m/px). MOLA does not resolve rover-scale hazards.</div>
    </div>
  )
}
