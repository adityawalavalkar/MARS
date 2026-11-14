import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useLoader, useThree } from '@react-three/fiber'
import { Line, OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { useMarsStore } from '../../store/useMarsStore.js'
import { terrainSpace } from '../../utils/terrain.js'
import { rampColor } from '../../utils/colors.js'
import { getLayerGrid, layerById, layerRange } from '../../utils/layers.js'
import { sampleAtLatLon, sampleGrid } from '../../utils/grid.js'
import { fmt, fmtCoord } from '../../utils/format.js'
import { MARS_TEXTURE_URL } from '../../config.js'

const OVERLAYS = ['elevation', 'hazard', 'slope']

function buildGeometry(grid, space, overlayGrid, overlayLayer, globalTexture = false) {
  const { width: w, height: h, bounds: b } = grid
  const pos = new Float32Array(w * h * 3)
  const col = new Float32Array(w * h * 3)
  const uv = new Float32Array(w * h * 2)
  const [oLo, oHi] = overlayGrid ? layerRange(overlayLayer, overlayGrid) : [0, 1]
  for (let r = 0; r < h; r++) {
    const lat = b.north - (r / (h - 1)) * (b.north - b.south)
    for (let c = 0; c < w; c++) {
      const lon = b.west + (c / (w - 1)) * (b.east - b.west)
      const i = r * w + c
      const e = grid.values[i]
      const [x, y, z] = space.toWorld(lat, lon, e)
      pos.set([x, y, z], i * 3)
      const u = c / (w - 1)
      const v = 1 - r / (h - 1)
      uv.set(globalTexture ? [((lon + 180) % 360) / 360, (lat + 90) / 180] : [u, v], i * 2)
      let rgb
      if (overlayGrid) {
        const s = sampleGrid(overlayGrid, c / (w - 1), 1 - r / (h - 1))
        const shade = Number.isFinite(s) ? rampColor(overlayLayer.ramp, (s - oLo) / (oHi - oLo || 1)) : [70, 40, 30]
        rgb = shade.map((v) => Math.round(255 * 0.45 + v * 0.55))
      } else {
        rgb = [255, 255, 255]
      }
      col.set([rgb[0] / 255, rgb[1] / 255, rgb[2] / 255], i * 3)
    }
  }
  const idx = new Uint32Array((w - 1) * (h - 1) * 6)
  let k = 0
  for (let r = 0; r < h - 1; r++) {
    for (let c = 0; c < w - 1; c++) {
      const a = r * w + c
      idx.set([a, a + w, a + 1, a + 1, a + w, a + w + 1], k)
      k += 6
    }
  }
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  g.setAttribute('color', new THREE.BufferAttribute(col, 3))
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
  g.setIndex(new THREE.BufferAttribute(idx, 1))
  g.computeVertexNormals()
  return g
}

function Scene({ readout, grid }) {
  const textureUrl = `${(import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')}/static/jezero_mola_texture.jpg`
  const region = useMarsStore((s) => s.selectedRegion)
  const globalTexture = region.id !== 'jezero'
  const texture = useLoader(THREE.TextureLoader, globalTexture ? MARS_TEXTURE_URL : textureUrl)
  const { gl } = useThree()
  const data = useMarsStore((s) => s.data)
  const { exaggeration, overlay3d } = useMarsStore((s) => s.settings)
  const start = useMarsStore((s) => s.start)
  const end = useMarsStore((s) => s.end)
  const route = useMarsStore((s) => s.data.route)
  const pickPoint = useMarsStore((s) => s.pickPoint)
  const marker = useRef(null)

  useEffect(() => {
    texture.colorSpace = THREE.SRGBColorSpace
    texture.generateMipmaps = true
    texture.minFilter = THREE.LinearMipmapLinearFilter
    texture.magFilter = THREE.LinearFilter
    texture.anisotropy = gl.capabilities.getMaxAnisotropy()
    texture.needsUpdate = true
  }, [texture, gl])

  const space = useMemo(() => terrainSpace(grid.bounds, grid.min, exaggeration), [grid, exaggeration])
  const overlayLayer = layerById(overlay3d)
  const overlayGrid = overlay3d === 'elevation' ? null : getLayerGrid(overlay3d, data)
  const geometry = useMemo(() => buildGeometry(grid, space, overlayGrid, overlayLayer, globalTexture), [grid, space, overlayGrid, overlayLayer, globalTexture])
  useEffect(() => () => geometry.dispose(), [geometry])

  const elevAt = (lat, lon) => sampleAtLatLon(grid, lat, lon)
  const toWorld = (lat, lon, lift = 0.06) => {
    const p = space.toWorld(lat, lon, elevAt(lat, lon))
    return [p[0], p[1] + lift, p[2]]
  }
  const routePts = useMemo(
    () => (route ? route.coordinates.map(([lon, lat]) => toWorld(lat, lon, 0.08)) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [route, space, grid],
  )

  const onMove = (e) => {
    const { lat, lon } = space.fromWorld(e.point.x, e.point.z)
    marker.current.visible = true
    marker.current.position.set(e.point.x, e.point.y + 0.12, e.point.z)
    const el = elevAt(lat, lon)
    const sl = sampleAtLatLon(data.elevation?.slope, lat, lon)
    readout.current.textContent = `${fmtCoord(lat, lon)}\nelev ${fmt(el)} m${region.id === 'jezero' ? ` · slope ${fmt(sl, 1)}°` : ''}`
  }
  const onOut = () => {
    marker.current.visible = false
    readout.current.textContent = 'Hover the terrain for coordinates'
  }
  const onClick = (e) => {
    if (region.id !== 'jezero') return
    if (e.delta > 5) return // ignore orbit drags
    const { lat, lon } = space.fromWorld(e.point.x, e.point.z)
    pickPoint(lat, lon)
  }

  const pin = (p, color) => (
    <group position={toWorld(p.lat, p.lon, 0)}>
      <mesh position={[0, 0.35, 0]}>
        <cylinderGeometry args={[0.02, 0.02, 0.7, 8]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh position={[0, 0.75, 0]}>
        <sphereGeometry args={[0.13, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  )

  return (
    <>
      <ambientLight intensity={0.55} color="#ffd9c0" />
      <directionalLight position={[8, 10, 5]} intensity={2.6} color="#ffe2c4" castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} />
      <hemisphereLight args={['#ffcfa8', '#2a1410', 0.5]} />
      <mesh geometry={geometry} castShadow receiveShadow onPointerMove={onMove} onPointerOut={onOut} onClick={onClick}>
        <meshStandardMaterial map={texture} vertexColors roughness={1} metalness={0} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={marker} visible={false}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      {start && pin(start, '#2fbfa5')}
      {end && pin(end, '#e5484d')}
      {routePts && (
        <>
          <Line points={routePts} color="#ff7a3d" lineWidth={9} transparent opacity={0.28} />
          <Line points={routePts} color="#fff1e0" lineWidth={2.5} />
        </>
      )}
      {route?.waypoints.map((w, i) => (
        <mesh key={i} position={toWorld(w.lat, w.lon, 0.1)}>
          <sphereGeometry args={[0.07, 12, 12]} />
          <meshBasicMaterial color="#ff7a3d" />
        </mesh>
      ))}
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} maxPolarAngle={Math.PI / 2.05} minDistance={3} maxDistance={32} target={[0, 0, 0]} />
      <gridHelper args={[space.W * 1.6, 16, '#7a3a20', '#4a2418']} position={[0, -0.02, 0]} />
      <fogExp2 attach="fog" args={['#3a1d14', 0.012]} />
    </>
  )
}

export default function Terrain3D() {
  const elevation = useMarsStore((s) => s.data.elevation)
  const region = useMarsStore((s) => s.selectedRegion)
  const status = useMarsStore((s) => s.status.elevation)
  const overlay = useMarsStore((s) => s.settings.overlay3d)
  const updateSettings = useMarsStore((s) => s.updateSettings)
  const readout = useRef(null)

  if (!elevation) {
    return (
      <div className="terrain-empty">
        <svg className="dunes" viewBox="0 0 800 220" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 160 L120 110 L210 150 L330 80 L450 140 L560 100 L680 150 L800 120 V220 H0Z" fill="#7a3a20" opacity=".55" />
          <path d="M0 190 C120 150 240 200 380 170 S640 150 800 185 V220 H0Z" fill="#3a1d14" opacity=".8" />
        </svg>
        <div className="empty empty-center">
          <strong>{status === 'loading' ? 'Loading terrain…' : status === 'error' ? 'Terrain data unavailable' : 'Awaiting terrain data'}</strong>
          <span>{status === 'loading' ? `Loading a real MOLA DEM for ${region.name}.` : `The 3D surface requires an elevation grid for ${region.name}.`}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="terrain">
      <Canvas dpr={[1, 1.5]} shadows="percentage" camera={{ position: [0, 8, 11], fov: 42, near: 0.1, far: 200 }} gl={{ antialias: true, alpha: true }}>
        <Scene readout={readout} grid={elevation.grid} />
      </Canvas>
      {!elevation.displayOnly && <div className="overlay-pick seg seg-mini" role="group" aria-label="Surface overlay">
        {OVERLAYS.map((o) => (
          <button key={o} type="button" className={overlay === o ? 'on' : ''} onClick={() => updateSettings({ overlay3d: o })}>
            {layerById(o).label}
          </button>
        ))}
      </div>}
      {elevation.displayOnly && <div className="terrain-source-note">{elevation.source} · regional display only; no route or hazard analysis</div>}
      <div className="map-readout" ref={readout}>Hover the terrain for coordinates</div>
    </div>
  )
}
