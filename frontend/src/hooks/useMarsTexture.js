import { useEffect, useState } from 'react'
import * as THREE from 'three'
import { MARS_TEXTURE_URL } from '../config.js'

// Loads the Mars colour map with real byte progress. Returns { texture, progress (0–1), failed }.
export function useMarsTexture() {
  const [state, setState] = useState({ texture: null, progress: 0, failed: false })

  useEffect(() => {
    let cancelled = false
    let objectUrl = null
    let texture = null
    ;(async () => {
      try {
        const res = await fetch(MARS_TEXTURE_URL)
        if (!res.ok || !res.body) throw new Error('texture request failed')
        const total = Number(res.headers.get('content-length')) || 0
        const reader = res.body.getReader()
        const chunks = []
        let received = 0
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          chunks.push(value)
          received += value.length
          if (!cancelled) {
            setState((s) => ({ ...s, progress: total ? Math.min(0.95, received / total) : Math.min(0.9, s.progress + 0.15) }))
          }
        }
        objectUrl = URL.createObjectURL(new Blob(chunks, { type: 'image/jpeg' }))
        texture = await new THREE.TextureLoader().loadAsync(objectUrl)
        texture.colorSpace = THREE.SRGBColorSpace
        texture.wrapS = THREE.RepeatWrapping
        texture.wrapT = THREE.ClampToEdgeWrapping
        texture.generateMipmaps = true
        texture.minFilter = THREE.LinearMipmapLinearFilter
        if (cancelled) {
          texture.dispose()
          return
        }
        setState({ texture, progress: 1, failed: false })
      } catch {
        if (!cancelled) setState({ texture: null, progress: 1, failed: true })
      }
    })()
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      if (texture) texture.dispose()
    }
  }, [])

  return state
}
