import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function radialTexture(stops, w = 256, h = 256) {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  const ctx = c.getContext('2d')
  const g = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2)
  stops.forEach(([o, col]) => g.addColorStop(o, col))
  ctx.fillStyle = g
  ctx.fillRect(0, 0, w, h)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  return t
}

// A partially cropped sun with bloom, corona, a faint horizontal streak and lens-flare ghosts.
export default function SunGlow({ position }) {
  const pulse = useRef()
  const tex = useMemo(
    () => ({
      core: radialTexture([[0, 'rgba(255,255,255,1)'], [0.18, 'rgba(255,238,205,1)'], [0.4, 'rgba(255,190,110,0.55)'], [1, 'rgba(255,140,60,0)']]),
      bloom: radialTexture([[0, 'rgba(255,200,140,0.55)'], [0.35, 'rgba(255,130,60,0.22)'], [1, 'rgba(255,90,30,0)']]),
      ghost: radialTexture([[0, 'rgba(255,170,100,0)'], [0.7, 'rgba(255,170,100,0.08)'], [0.85, 'rgba(255,200,150,0.22)'], [1, 'rgba(255,170,100,0)']]),
      streak: radialTexture([[0, 'rgba(255,220,170,0.7)'], [1, 'rgba(255,160,80,0)']]),
    }),
    [],
  )
  useEffect(() => () => Object.values(tex).forEach((t) => t.dispose()), [tex])

  useFrame((state) => {
    if (pulse.current) pulse.current.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 0.8) * 0.03)
  })

  const ghosts = [
    [0.3, 0.9],
    [0.55, 0.55],
    [0.8, 1.3],
  ]
  const common = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }

  return (
    <group>
      <group position={position} ref={pulse}>
        <sprite scale={[9, 9, 1]}>
          <spriteMaterial map={tex.bloom} {...common} />
        </sprite>
        <sprite scale={[14, 0.5, 1]}>
          <spriteMaterial map={tex.streak} {...common} opacity={0.22} />
        </sprite>
        <sprite scale={[2.4, 2.4, 1]}>
          <spriteMaterial map={tex.core} {...common} />
        </sprite>
      </group>
      {ghosts.map(([k, s]) => (
        <sprite key={k} position={[position.x * (1 - k), position.y * (1 - k), position.z]} scale={[s, s, 1]}>
          <spriteMaterial map={tex.ghost} {...common} opacity={0.4} />
        </sprite>
      ))}
    </group>
  )
}
