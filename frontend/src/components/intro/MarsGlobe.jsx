import { useEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

const shellVertex = /* glsl */ `
  varying vec3 vWorldNormal;
  varying vec3 vViewNormal;
  varying vec3 vViewPos;
  void main() {
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    vViewNormal = normalize(normalMatrix * normal);
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vViewPos = mv.xyz;
    gl_Position = projectionMatrix * mv;
  }
`
// Fresnel glow, brighter on the sun-facing side. BackSide shell = outer halo, FrontSide = thin inner rim.
const atmosphereFragment = /* glsl */ `
  uniform vec3 uSunDir;
  uniform vec3 uColor;
  uniform float uPower;
  uniform float uStrength;
  uniform float uFade;
  uniform float uBack;
  varying vec3 vWorldNormal;
  varying vec3 vViewNormal;
  void main() {
    vec3 n = normalize(vViewNormal);
    float f = uBack > 0.5 ? pow(max(0.0, 0.72 - dot(n, vec3(0.0, 0.0, 1.0))), uPower)
                          : pow(max(0.0, 1.0 - dot(n, vec3(0.0, 0.0, 1.0))), uPower);
    float sun = 0.2 + 0.8 * smoothstep(-0.35, 0.55, dot(normalize(vWorldNormal), uSunDir));
    gl_FragColor = vec4(uColor, 1.0) * f * sun * uStrength * uFade;
  }
`
// Soft terminator: dark, slightly warm falloff on the night side (mesh is static, so world normals are stable).
const terminatorFragment = /* glsl */ `
  uniform vec3 uSunDir;
  uniform float uFade;
  varying vec3 vWorldNormal;
  void main() {
    float d = dot(normalize(vWorldNormal), uSunDir);
    float night = smoothstep(0.22, -0.38, d);
    float twilight = smoothstep(0.25, 0.0, abs(d)) * 0.12;
    vec3 col = mix(vec3(0.01, 0.005, 0.01), vec3(0.35, 0.09, 0.03), twilight);
    gl_FragColor = vec4(col, night * 0.5 * uFade);
  }
`

function useDerivedBump(texture) {
  const bump = useMemo(() => {
    const img = texture?.image
    if (!img) return null
    const c = document.createElement('canvas')
    c.width = img.width
    c.height = img.height
    const ctx = c.getContext('2d')
    ctx.drawImage(img, 0, 0)
    const data = ctx.getImageData(0, 0, c.width, c.height)
    const px = data.data
    for (let i = 0; i < px.length; i += 4) {
      const g = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
      px[i] = px[i + 1] = px[i + 2] = g
    }
    ctx.putImageData(data, 0, 0)
    const t = new THREE.CanvasTexture(c)
    t.wrapS = THREE.RepeatWrapping
    t.anisotropy = 8
    return t
  }, [texture])
  useEffect(() => () => bump?.dispose(), [bump])
  return bump
}

export default function MarsGlobe({ texture, sunDir, tl }) {
  const gl = useThree((s) => s.gl)
  const group = useRef()
  const mat = useRef()
  const globeTexture = useMemo(() => {
    if (!texture) return texture
    const optimized = texture.clone()
    optimized.anisotropy = gl.capabilities.getMaxAnisotropy()
    optimized.needsUpdate = true
    return optimized
  }, [texture, gl])
  const bump = useDerivedBump(globeTexture)

  const shared = useMemo(() => ({ uSunDir: { value: sunDir.clone() }, uFade: { value: 0 } }), [sunDir])
  const halo = useMemo(
    () => ({ ...shared, uColor: { value: new THREE.Color('#ff8a4a') }, uPower: { value: 3.2 }, uStrength: { value: 1.6 }, uBack: { value: 1 } }),
    [shared],
  )
  const rim = useMemo(
    () => ({ ...shared, uColor: { value: new THREE.Color('#ffb48a') }, uPower: { value: 3.4 }, uStrength: { value: 0.9 }, uBack: { value: 0 } }),
    [shared],
  )

  // oxlint-disable react/immutability -- Three.js uniforms and refs update in the render loop.
  useFrame((_, delta) => {
    const { fade, spin } = tl.current
    group.current.rotation.y += delta * spin
    group.current.scale.setScalar(0.82 + 0.18 * fade)
    mat.current.opacity = fade
    mat.current.transparent = fade < 0.999
    shared.uFade.value = fade
  })
  // oxlint-enable react/immutability

  return (
    <group>
      <group rotation={[0, 0, 0.44]}>
        <group ref={group}>
          <mesh>
            <sphereGeometry args={[1, 128, 128]} />
            <meshStandardMaterial
              ref={mat}
              map={globeTexture}
              color={globeTexture ? '#ffffff' : '#8a3a1a'}
              bumpMap={bump}
              bumpScale={1.2}
              roughness={0.95}
              metalness={0}
            />
          </mesh>
        </group>
      </group>
      <mesh scale={1.004}>
        <sphereGeometry args={[1, 96, 96]} />
        <shaderMaterial uniforms={shared} vertexShader={shellVertex} fragmentShader={terminatorFragment} transparent depthWrite={false} />
      </mesh>
      <mesh scale={1.012}>
        <sphereGeometry args={[1, 96, 96]} />
        <shaderMaterial uniforms={rim} vertexShader={shellVertex} fragmentShader={atmosphereFragment} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh scale={1.1}>
        <sphereGeometry args={[1, 96, 96]} />
        <shaderMaterial uniforms={halo} vertexShader={shellVertex} fragmentShader={atmosphereFragment} transparent depthWrite={false} side={THREE.BackSide} blending={THREE.AdditiveBlending} />
      </mesh>
      <directionalLight position={sunDir.clone().multiplyScalar(12)} intensity={1.25} color="#fff1e0" />
      <ambientLight intensity={0.22} color="#7a86d8" />
    </group>
  )
}
