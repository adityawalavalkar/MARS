// Helpers for backend grids. Convention: row 0 is the NORTH edge, column 0 is the WEST edge.

export function normalizeBounds(b) {
  if (!b) return null
  if (Array.isArray(b) && b.length === 2 && Array.isArray(b[0])) {
    return { south: b[0][0], west: b[0][1], north: b[1][0], east: b[1][1] }
  }
  const { south, west, north, east } = b
  return [south, west, north, east].every(Number.isFinite) ? { south, west, north, east } : null
}

export function normalizeGrid(raw, fallbackBounds) {
  if (!raw || typeof raw !== 'object') return null
  let { width, height, values } = raw
  if (Array.isArray(values) && Array.isArray(values[0])) {
    height = values.length
    width = values[0].length
    values = values.flat()
  }
  if (!Array.isArray(values) && !ArrayBuffer.isView(values)) return null
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 2 || height < 2) return null
  if (values.length !== width * height) return null
  const data = Float32Array.from(values, (v) => (Number.isFinite(v) ? v : NaN))
  let min = Infinity
  let max = -Infinity
  for (const v of data) {
    if (v < min) min = v
    if (v > max) max = v
  }
  if (!Number.isFinite(min)) return null
  return {
    width,
    height,
    values: data,
    min: Number.isFinite(raw.min) ? raw.min : min,
    max: Number.isFinite(raw.max) ? raw.max : max,
    bounds: normalizeBounds(raw.bounds) || fallbackBounds || null,
  }
}

// u: 0 (west) → 1 (east); v: 0 (south) → 1 (north). Bilinear sample; NaN outside / on gaps.
export function sampleGrid(grid, u, v) {
  if (!grid || u < 0 || u > 1 || v < 0 || v > 1) return NaN
  const x = u * (grid.width - 1)
  const y = (1 - v) * (grid.height - 1)
  const x0 = Math.floor(x)
  const y0 = Math.floor(y)
  const x1 = Math.min(x0 + 1, grid.width - 1)
  const y1 = Math.min(y0 + 1, grid.height - 1)
  const fx = x - x0
  const fy = y - y0
  const g = grid.values
  const w = grid.width
  const top = g[y0 * w + x0] * (1 - fx) + g[y0 * w + x1] * fx
  const bot = g[y1 * w + x0] * (1 - fx) + g[y1 * w + x1] * fx
  return top * (1 - fy) + bot * fy
}

export function latLonToUV(bounds, lat, lon) {
  return {
    u: (lon - bounds.west) / (bounds.east - bounds.west),
    v: (lat - bounds.south) / (bounds.north - bounds.south),
  }
}

export function sampleAtLatLon(grid, lat, lon, fallbackBounds) {
  const b = grid?.bounds || fallbackBounds
  if (!grid || !b) return NaN
  const { u, v } = latLonToUV(b, lat, lon)
  return sampleGrid(grid, u, v)
}
