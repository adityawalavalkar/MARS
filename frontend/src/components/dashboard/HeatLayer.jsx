import { useMemo } from 'react'
import { ImageOverlay } from 'react-leaflet'
import { rampColor } from '../../utils/colors.js'
import { layerRange } from '../../utils/layers.js'

// Paints a backend grid into a smooth canvas image and overlays it on the map. Low values are more transparent
// so the imagery shows through. Renders nothing until `grid` exists.
function paint(grid, layer) {
  const small = document.createElement('canvas')
  small.width = grid.width
  small.height = grid.height
  const sctx = small.getContext('2d')
  const img = sctx.createImageData(grid.width, grid.height)
  const [lo, hi] = layerRange(layer, grid)
  const span = hi - lo || 1
  for (let i = 0; i < grid.values.length; i++) {
    const v = grid.values[i]
    const o = i * 4
    if (!Number.isFinite(v)) continue
    const t = Math.min(1, Math.max(0, (v - lo) / span))
    const [r, g, b] = rampColor(layer.ramp, t)
    img.data[o] = r
    img.data[o + 1] = g
    img.data[o + 2] = b
    img.data[o + 3] = 90 + 165 * t
  }
  sctx.putImageData(img, 0, 0)
  const big = document.createElement('canvas')
  const scale = Math.max(1, Math.min(4, Math.floor(768 / Math.max(grid.width, grid.height))))
  big.width = grid.width * scale
  big.height = grid.height * scale
  const bctx = big.getContext('2d')
  bctx.imageSmoothingEnabled = true
  bctx.imageSmoothingQuality = 'high'
  bctx.drawImage(small, 0, 0, big.width, big.height)
  return big.toDataURL('image/png')
}

export default function HeatLayer({ grid, layer, opacity, fallbackBounds }) {
  const url = useMemo(() => (grid ? paint(grid, layer) : null), [grid, layer])
  if (!grid || !url) return null
  const b = grid.bounds || fallbackBounds
  return <ImageOverlay key={layer.id} url={url} bounds={[[b.south, b.west], [b.north, b.east]]} opacity={opacity} zIndex={400} />
}
