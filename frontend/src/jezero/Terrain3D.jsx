import { useEffect, useMemo, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { useJez } from './store.js'

function loadImg(src) { return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src }) }

function Surface({ mesh, tex, exag, onPick }) {
  const geo = useMemo(() => {
    const { rows: M, cols: N, z, width_m, height_m, z_min } = mesh; const pos = new Float32Array(M * N * 3), uv = new Float32Array(M * N * 2), idx = []
    for (let i = 0; i < M; i++) for (let j = 0; j < N; j++) {
      const k = i * N + j; pos[k * 3] = (j / (N - 1) - 0.5) * width_m / 1000; pos[k * 3 + 1] = (z[i][j] - z_min) * exag / 1000; pos[k * 3 + 2] = (i / (M - 1) - 0.5) * height_m / 1000
      uv[k * 2] = j / (N - 1); uv[k * 2 + 1] = 1 - i / (M - 1)
      if (i < M - 1 && j < N - 1) { idx.push(k, k + N, k + 1, k + 1, k + N, k + N + 1) }
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals(); return g
  }, [mesh, exag])
  return <mesh geometry={geo} onClick={onPick}><meshStandardMaterial map={tex} roughness={1} metalness={0} /></mesh>
}

function RouteLine({ mesh, coords, color, exag }) {
  const [S, W, N, E] = mesh.bounds_swne
  const pts = useMemo(() => coords.map(([lon, lat, z]) => new THREE.Vector3(((lon - W) / (E - W) - 0.5) * mesh.width_m / 1000, (z - mesh.z_min) * exag / 1000 + 0.04, ((N - lat) / (N - S) - 0.5) * mesh.height_m / 1000)), [coords, mesh, exag, S, W, N, E])
  return <line><bufferGeometry attach="geometry" setFromPoints={pts} /><lineBasicMaterial attach="material" color={color} linewidth={2} /></line>
}

export default function Terrain3D() {
  const exag = useJez((s) => s.exag); const setExag = useJez((s) => s.setExag); const route = useJez((s) => s.route); const active = useJez((s) => s.activeRoute)
  const mode = useJez((s) => s.mode); const customPts = useJez((s) => s.customPts); const pickCustom = useJez((s) => s.pickCustom)
  const [mesh, setMesh] = useState(null); const [tex, setTex] = useState(null); const [err, setErr] = useState(null)
  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [m, el, hs] = await Promise.all([fetch('/jezero/jezero_terrain_mesh_20m.json').then((r) => { if (!r.ok) throw new Error('mesh'); return r.json() }), loadImg('/jezero/elevation.png'), loadImg('/jezero/hillshade.png')])
        const c = document.createElement('canvas'); c.width = el.width; c.height = el.height; const g = c.getContext('2d')
        g.drawImage(el, 0, 0); g.globalCompositeOperation = 'multiply'; g.drawImage(hs, 0, 0, c.width, c.height)
        const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter
        if (alive) { setMesh(m); setTex(t) }
      } catch (e) { if (alive) setErr(e.message) }
    })()
    return () => { alive = false }
  }, [])
  if (err) return <div className="terrain-empty"><strong>3D terrain unavailable</strong><span>Mesh or overlay files missing. Run the preprocessing script.</span></div>
  if (!mesh || !tex) return <div className="terrain-empty">Building 3D terrain from the 20 m CTX DEM…</div>
  const act = route && !route.error ? route[active] : null
  const [south, west, north, east] = mesh.bounds_swne
  const pickTerrain = (event) => {
    if (mode !== 'custom' || event.delta > 5) return
    event.stopPropagation()
    const u = Math.max(0, Math.min(1, event.point.x / (mesh.width_m / 1000) + 0.5))
    const v = Math.max(0, Math.min(1, event.point.z / (mesh.height_m / 1000) + 0.5))
    pickCustom(north - v * (north - south), west + u * (east - west))
  }
  const markerPositions = customPts.map((point, index) => {
    const col = Math.max(0, Math.min(mesh.cols - 1, Math.round(((point.lon - west) / (east - west)) * (mesh.cols - 1))))
    const row = Math.max(0, Math.min(mesh.rows - 1, Math.round(((north - point.lat) / (north - south)) * (mesh.rows - 1))))
    return {
      key: `${point.lat}-${point.lon}-${index}`,
      position: [((point.lon - west) / (east - west) - 0.5) * mesh.width_m / 1000, (mesh.z[row][col] - mesh.z_min) * exag / 1000 + 0.18, ((north - point.lat) / (north - south) - 0.5) * mesh.height_m / 1000],
      color: index === 0 ? '#3ddc97' : '#ff4d5a',
    }
  })
  return (
    <div className="map-wrap jz-3d">
      <Canvas camera={{ position: [0, 55, 70], fov: 45, near: 0.05, far: 600 }} gl={{ antialias: true }} dpr={[1, 2]}>
        <color attach="background" args={['#05090d']} /><ambientLight intensity={0.55} /><directionalLight position={[-40, 60, -30]} intensity={1.6} />
        <Surface mesh={mesh} tex={tex} exag={exag} onPick={pickTerrain} />
        {markerPositions.map((marker) => <mesh key={marker.key} position={marker.position}><sphereGeometry args={[0.24, 14, 14]} /><meshBasicMaterial color={marker.color} /></mesh>)}
        {act && <RouteLine mesh={mesh} coords={act.coordinates} exag={exag} color={active === 'fast' ? '#00e5ff' : '#ffb000'} />}
        <OrbitControls maxPolarAngle={1.5} />
      </Canvas>
      <div className="jz-3d-ctl"><label>Vertical exaggeration <b>{exag.toFixed(1)}×</b><input type="range" min="1" max="6" step="0.5" value={exag} onChange={(e) => setExag(Number(e.target.value))} /></label>
        <small>Terrain: 512×512 mesh of the 20 m CTX DEM (block mean, ~175 m cells). Texture: elevation tint × hillshade.</small></div>
      <div className="hud-note">{mode === 'custom' ? `Custom 2-point: click for START then END (${customPts.length}/2). Click Calculate in Mission brief.` : 'Switch to Custom 2-point to choose a START and END on the 3D terrain.'}</div>
      <div className="hud-corners" aria-hidden="true"><i /><i /><i /><i /></div>
    </div>
  )
}
