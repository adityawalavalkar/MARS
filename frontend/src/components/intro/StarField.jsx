import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const vertex = /* glsl */ `
  attribute float aSize;
  attribute float aPhase;
  attribute float aSpeed;
  attribute vec3 aTint;
  uniform float uTime;
  uniform float uPixel;
  varying float vTwinkle;
  varying vec3 vTint;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    vTwinkle = 0.55 + 0.45 * sin(uTime * aSpeed + aPhase);
    vTint = aTint;
    gl_PointSize = aSize * uPixel * (0.6 + 0.4 * vTwinkle);
  }
`
const fragment = /* glsl */ `
  varying float vTwinkle;
  varying vec3 vTint;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, d);
    gl_FragColor = vec4(vTint, a * vTwinkle);
  }
`

// Deterministic PRNG so star layouts are pure (same sky every load).
function mulberry32(seed) {
  let a = seed
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function Layer({ count, radius, size, parallax, drift, twinkle }) {
  const group = useRef()
  const material = useRef()
  const geometry = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const sizes = new Float32Array(count)
    const phase = new Float32Array(count)
    const speed = new Float32Array(count)
    const tint = new Float32Array(count * 3)
    const rand = mulberry32(Math.round(radius * 131 + count))
    const palette = [new THREE.Color('#ffffff'), new THREE.Color('#bcd2ff'), new THREE.Color('#ffd9bd')]
    for (let i = 0; i < count; i++) {
      const r = radius * (1 + rand() * 0.6)
      const theta = rand() * Math.PI * 2
      const phi = Math.acos(2 * rand() - 1)
      pos.set([r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta)], i * 3)
      sizes[i] = size * (0.5 + rand())
      phase[i] = rand() * 6.28
      speed[i] = twinkle * (0.5 + rand())
      const c = palette[Math.floor(rand() * palette.length)]
      tint.set([c.r, c.g, c.b], i * 3)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    g.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
    g.setAttribute('aPhase', new THREE.BufferAttribute(phase, 1))
    g.setAttribute('aSpeed', new THREE.BufferAttribute(speed, 1))
    g.setAttribute('aTint', new THREE.BufferAttribute(tint, 3))
    return g
  }, [count, radius, size, twinkle])

  const uniforms = useMemo(() => ({ uTime: { value: 0 }, uPixel: { value: 1 } }), [])

  // oxlint-disable react/immutability -- Three.js uniforms and refs update in the render loop.
  useFrame((state, delta) => {
    uniforms.uTime.value = state.clock.elapsedTime
    uniforms.uPixel.value = state.gl.getPixelRatio()
    const g = group.current
    g.rotation.y += delta * drift
    g.position.x += (state.pointer.x * parallax - g.position.x) * 0.04
    g.position.y += (state.pointer.y * parallax - g.position.y) * 0.04
  })
  // oxlint-enable react/immutability

  return (
    <group ref={group}>
      <points geometry={geometry} frustumCulled={false}>
        <shaderMaterial
          ref={material}
          uniforms={uniforms}
          vertexShader={vertex}
          fragmentShader={fragment}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  )
}

// Three parallax layers: far (many, tiny), mid, near (few, large).
export default function StarField() {
  return (
    <>
      <Layer count={1600} radius={70} size={2.2} parallax={0.6} drift={0.004} twinkle={1.2} />
      <Layer count={500} radius={45} size={3.6} parallax={1.6} drift={0.008} twinkle={1.8} />
      <Layer count={90} radius={28} size={6} parallax={3.2} drift={0.014} twinkle={2.4} />
    </>
  )
}
