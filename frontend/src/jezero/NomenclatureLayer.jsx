import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, Marker, Polygon, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useMarsStore } from '../store/useMarsStore.js'
import { JEZERO_REGION } from '../config.js'

const R = 3396190
const ring = (lat, lon, km) => Array.from({ length: 73 }, (_, i) => { const a = (i / 72) * 2 * Math.PI, d = (km * 1000) / R; return [lat + (d * Math.cos(a) * 180) / Math.PI, lon + ((d * Math.sin(a)) / Math.cos((lat * Math.PI) / 180) * 180) / Math.PI] })
const pulse = L.divIcon({ className: 'jz-pulse', html: '<span></span><b></b>', iconSize: [28, 28], iconAnchor: [14, 14] })
const minKm = (z) => (z < 3 ? 600 : z < 4 ? 300 : z < 5 ? 150 : 0)

// Global map labels come from the nomenclature JSON (IAU/USGS). Only Jezero is clickable; everything else is greyed "coming soon".
export default function NomenclatureLayer({ zoom }) {
  const map = useMap(); const setRegion = useMarsStore((s) => s.setRegion); const [data, setData] = useState([])
  useEffect(() => { fetch('/jezero/nomenclature.json').then((r) => r.json()).then((j) => setData(j.features)).catch(() => setData([])) }, [])
  const shown = useMemo(() => data.filter((n) => n.name !== 'Jezero' && n.tier === 'regional' && n.diameter_km >= minKm(zoom)), [data, zoom])
  const jez = data.find((n) => n.name === 'Jezero') ?? { lat: 18.4082, lon: 77.6873, diameter_km: 47.5 }
  const open = () => { map.flyTo([jez.lat, jez.lon], 8.5, { duration: 1.3 }); window.setTimeout(() => setRegion(JEZERO_REGION), 1400) }
  return (
    <>
      {shown.map((n) => (
        <CircleMarker key={n.name} center={[n.lat, n.lon]} radius={4} pathOptions={{ color: '#6d7882', fillColor: '#6d7882', fillOpacity: 0.7, weight: 1 }}>
          <Tooltip permanent direction="top" className="region-label region-label-global jz-grey">{n.name}<br /><small>coming soon</small></Tooltip>
        </CircleMarker>
      ))}
      <Polygon positions={ring(jez.lat, jez.lon, jez.diameter_km / 2)} pathOptions={{ color: '#ffb000', weight: 2, fillOpacity: 0.08 }} eventHandlers={{ click: open }} />
      <Marker position={[jez.lat, jez.lon]} icon={pulse} eventHandlers={{ click: open }}>
        <Tooltip permanent direction="top" className="region-label region-label-jezero"><b>Jezero</b><br /><small>click to enter</small></Tooltip>
      </Marker>
    </>
  )
}
