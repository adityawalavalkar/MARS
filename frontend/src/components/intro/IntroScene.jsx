import { useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { useMarsTexture } from '../../hooks/useMarsTexture.js'
import StarField from './StarField.jsx'
import SunGlow from './SunGlow.jsx'
import MarsGlobe from './MarsGlobe.jsx'
import LoadingOverlay from './LoadingOverlay.jsx'

const BASE_Z = 4.4
const END_Z = 1.1
const FOV = 45
const T_FADE = 2
const T_SPIN = 5
const T_END = 6.5

const clamp01 = (x) => Math.min(1, Math.max(0, x))
const easeOutCubic = (x) => 1 - Math.pow(1 - x, 3)
const easeInOutCubic = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2)

// Drives the whole timeline. Starts only once the texture is ready (or failed), then:
// 0–2s fade/scale in + slow spin, 2–5s accelerating spin, 5–6.5s dolly into the surface.
function Scene({ texture, ready, loadProgress, tl, onDone }) {
  const size = useThree((s) => s.size)
  const doneRef = useRef(false)

  const sunPos = useMemo(() => {
    const dist = BASE_Z + 0.5
    const hh = dist * Math.tan(THREE.MathUtils.degToRad(FOV / 2))
    const hw = hh * (size.width / size.height)
    return new THREE.Vector3(-hw * 0.92, -hh * 0.78, 1.2)
  }, [size])
  const sunDir = useMemo(() => sunPos.clone().normalize(), [sunPos])

  // oxlint-disable react/immutability -- tl is mutable animation-loop state held in a ref.
  useFrame((state, delta) => {
    const s = tl.current
    if (ready) s.t += Math.min(delta, 0.1)
    const t = s.t
    s.fade = easeOutCubic(clamp01(t / T_FADE))
    s.spin = t < T_FADE ? 0.1 : t < T_SPIN ? 0.1 + 1.5 * Math.pow((t - T_FADE) / (T_SPIN - T_FADE), 2) : 1.6
    s.zoom = easeInOutCubic(clamp01((t - T_SPIN) / (T_END - T_SPIN)))
    const timeline = easeOutCubic(clamp01(t / T_SPIN))
    s.progress = ready ? 0.2 + 0.8 * timeline : loadProgress * 0.2
    state.camera.position.z = BASE_Z + (END_Z - BASE_Z) * s.zoom
    state.camera.lookAt(0, 0, 0)
    if (ready && t >= T_END && !doneRef.current) {
      doneRef.current = true
      onDone()
    }
  })
  // oxlint-enable react/immutability

  return (
    <>
      <StarField />
      <SunGlow position={sunPos} />
      <MarsGlobe texture={texture} sunDir={sunDir} tl={tl} />
    </>
  )
}

export default function IntroScene({ onDone }) {
  const { texture, progress, failed } = useMarsTexture()
  const tl = useRef({ t: 0, fade: 0, spin: 0.1, zoom: 0, progress: 0 })
  const stageRef = useRef(null)
  const ready = !!texture || failed

  return (
    <div className="intro">
      <div className="intro-stage" ref={stageRef}>
        <Canvas
          dpr={[1, 2]}
          camera={{ fov: FOV, position: [0, 0, BASE_Z], near: 0.05, far: 300 }}
          gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        >
          <Scene texture={texture} ready={ready} loadProgress={progress} tl={tl} onDone={onDone} />
        </Canvas>
      </div>
      <LoadingOverlay tl={tl} stageRef={stageRef} failed={failed} onSkip={onDone} />
    </div>
  )
}
