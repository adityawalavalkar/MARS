export default function Skeleton({ width = '100%', height = 14, radius = 8, style }) {
  return <span className="skeleton" style={{ width, height, borderRadius: radius, ...style }} aria-hidden="true" />
}
