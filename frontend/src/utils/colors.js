// Colour ramps used by the map heat layers, 3D overlays and legends.

export const RAMPS = {
  hazard: [[0, [47, 191, 165]], [0.35, [226, 196, 96]], [0.65, [255, 122, 61]], [1, [229, 72, 77]]],
  elevation: [[0, [42, 20, 16]], [0.4, [140, 62, 30]], [0.75, [214, 140, 96]], [1, [243, 217, 204]]],
  slope: [[0, [243, 217, 204]], [0.5, [214, 110, 60]], [1, [140, 30, 20]]],
  radiation: [[0, [47, 120, 191]], [0.5, [255, 160, 80]], [1, [255, 240, 220]]],
  mineral: [[0, [42, 20, 16]], [0.5, [193, 68, 14]], [1, [255, 214, 130]]],
}

export function rampColor(ramp, t) {
  const x = Math.min(1, Math.max(0, t))
  for (let i = 1; i < ramp.length; i++) {
    if (x <= ramp[i][0]) {
      const [t0, c0] = ramp[i - 1]
      const [t1, c1] = ramp[i]
      const f = (x - t0) / (t1 - t0 || 1)
      return [c0[0] + (c1[0] - c0[0]) * f, c0[1] + (c1[1] - c0[1]) * f, c0[2] + (c1[2] - c0[2]) * f]
    }
  }
  return ramp[ramp.length - 1][1]
}

export function cssGradient(ramp) {
  const stops = ramp.map(([t, c]) => `rgb(${c[0]},${c[1]},${c[2]}) ${Math.round(t * 100)}%`)
  return `linear-gradient(90deg, ${stops.join(', ')})`
}
