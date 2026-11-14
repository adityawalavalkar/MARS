import { RAMPS } from './colors.js'

// Heat-map layers. `fixed` = fixed value range, otherwise the grid's own min/max is used.
export const LAYERS = [
  { id: 'none', label: 'Natural', unit: '', ramp: [[0, [40, 40, 40]], [1, [40, 40, 40]]], fixed: [0, 1] },
  { id: 'hazard', label: 'Hazard', unit: '', ramp: RAMPS.hazard, fixed: [0, 1] },
  { id: 'elevation', label: 'Elevation', unit: 'm', ramp: RAMPS.elevation },
  { id: 'slope', label: 'Slope', unit: '°', ramp: RAMPS.slope },
]

export const layerById = (id) => LAYERS.find((l) => l.id === id) || LAYERS[1]

// Returns the grid backing a layer (or null while the backend has not provided it).
export function getLayerGrid(id, data) {
  switch (id) {
    case 'none':
      return null
    case 'hazard':
      return data.hazard?.grid || null
    case 'elevation':
      return data.elevation?.grid || null
    case 'slope':
      return data.elevation?.slope || null
    case 'radiation':
      return data.radiation?.grid || null
    case 'mineral':
      return data.mineral?.grid || null
    default:
      return null
  }
}

export function layerRange(layer, grid) {
  if (layer.fixed) return layer.fixed
  return grid ? [grid.min, grid.max] : [0, 1]
}
