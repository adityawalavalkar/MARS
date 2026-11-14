// Maps lat/lon/elevation ↔ 3D world units for the terrain mesh. North is −Z, up is +Y.
const KM_PER_DEG = 59.2 // Mars: 2π·3389.5 km / 360
const SIZE = 10

export function terrainSpace(bounds, minElev, exaggeration) {
  const midLat = (bounds.north + bounds.south) / 2
  const kmX = (bounds.east - bounds.west) * KM_PER_DEG * Math.cos((midLat * Math.PI) / 180)
  const kmZ = (bounds.north - bounds.south) * KM_PER_DEG
  const unit = SIZE / Math.max(kmX, kmZ, 1e-6)
  const W = kmX * unit
  const D = kmZ * unit
  const yScale = (unit / 1000) * exaggeration
  return {
    W,
    D,
    toWorld(lat, lon, elev) {
      return [
        ((lon - bounds.west) / (bounds.east - bounds.west)) * W - W / 2,
        ((Number.isFinite(elev) ? elev : minElev) - minElev) * yScale,
        -(((lat - bounds.south) / (bounds.north - bounds.south)) * D - D / 2),
      ]
    },
    fromWorld(x, z) {
      return {
        lon: bounds.west + ((x + W / 2) / W) * (bounds.east - bounds.west),
        lat: bounds.south + ((-z + D / 2) / D) * (bounds.north - bounds.south),
      }
    },
  }
}
