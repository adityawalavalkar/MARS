import { useEffect, useMemo, useState } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { getPov } from './api.js'
import { useJez } from './store.js'

const bearing = (a, b) => { const r = Math.PI / 180, dl = (b.lon - a.lon) * r; const y = Math.sin(dl) * Math.cos(b.lat * r), x = Math.cos(a.lat * r) * Math.sin(b.lat * r) - Math.sin(a.lat * r) * Math.cos(b.lat * r) * Math.cos(dl); return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360 }

function Scene({ patch, heading }) {
  const { camera } = useThree()
  const { geo, eye } = useMemo(() => {
    const n = patch.n, c = patch.cell_m, h = patch.center_index, z0 = patch.z[h][h]; const pos = new Float32Array(n * n * 3), col = new Float32Array(n * n * 3), idx = []
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      const k = i * n + j, zz = patch.z[i][j] - z0; pos.set([(j - h) * c, zz, (i - h) * c], k * 3)
      const dzx = ((patch.z[i][Math.min(j + 1, n - 1)] - patch.z[i][Math.max(j - 1, 0)]) / (2 * c)), dzy = ((patch.z[Math.min(i + 1, n - 1)][j] - patch.z[Math.max(i - 1, 0)][j]) / (2 * c))
      const sl = Math.min(Math.hypot(dzx, dzy) * 2.2, 1); col.set([0.62 - 0.3 * sl, 0.40 - 0.2 * sl, 0.28 - 0.15 * sl], k * 3)
      if (i < n - 1 && j < n - 1) idx.push(k, k + n, k + 1, k + 1, k + n, k + n + 1)
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.setIndex(idx); g.computeVertexNormals()
    return { geo: g, eye: 1.7 }
  }, [patch])
  useEffect(() => {
    const r = (heading * Math.PI) / 180; camera.position.set(0, eye, 0); camera.lookAt(Math.sin(r) * 100, eye - 1.5, -Math.cos(r) * 100); camera.far = 4000; camera.updateProjectionMatrix()
  }, [camera, heading, eye])
  return (<><color attach="background" args={['#b98a6a']} /><fog attach="fog" args={['#b98a6a', 300, 2200]} /><hemisphereLight args={['#f3d9cc', '#4a2a1a', 0.9]} /><directionalLight position={[-300, 400, 200]} intensity={1.4} />
    <mesh geometry={geo}><meshStandardMaterial vertexColors roughness={1} flatShading={false} side={THREE.DoubleSide} /></mesh></>)
}

export default function PovPanel() {
  const route = useJez((s) => s.route); const active = useJez((s) => s.activeRoute); const sel = useJez((s) => s.selWp); const setSel = useJez((s) => s.setSelWp)
  const [patch, setPatch] = useState(null)
  const wps = route && !route.error ? route[active].waypoints : []
  const w = wps[sel] ?? wps[0]; const nxt = wps[(sel ?? 0) + 1]
  const heading = w && nxt ? bearing(w, nxt) : 0
  useEffect(() => { let alive = true; if (w) getPov(w.lat, w.lon).then((p) => alive && setPatch(p.error ? null : p)); return () => { alive = false } }, [w?.lat, w?.lon]) // eslint-disable-line
  if (!w) return <section className="jz-card"><h3>Waypoint POV</h3><p className="dim">Calculate a route to see the synthetic view at each waypoint.</p></section>
  return (
    <section className="jz-card">
      <h3>Waypoint POV</h3>
      <div className="jz-tabs">{wps.map((x, i) => <button key={i} className={i === sel ? 'on' : ''} onClick={() => setSel(i)}>{route[active].names?.[i] ?? x.id}</button>)}</div>
      <div className="pov-frame">
        {patch ? <Canvas dpr={[1, 1.5]} camera={{ fov: 60, near: 0.5 }}><Scene patch={patch} heading={heading} /></Canvas> : <div className="terrain-empty">Loading local 20 m DEM patch…</div>}
        <div className="pov-hud"><span>HDG {nxt ? `${heading.toFixed(0)}° to next waypoint` : 'final waypoint'}</span><span>EYE +1.7 m</span></div>
      </div>
      <small className="dim">Synthetic view from 20 m CTX DEM (3.2 km patch, 20 m cells; not a camera image).</small>
    </section>
  )
}
