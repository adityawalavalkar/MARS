import { useEffect, useRef, useState } from 'react'

// Animates a number towards `target`. Returns null while there is no finite target.
export function useCountUp(target, duration = 900) {
  const [value, setValue] = useState(0)
  const fromRef = useRef(0)
  useEffect(() => {
    if (!Number.isFinite(target)) return undefined
    const from = fromRef.current
    const start = performance.now()
    let raf
    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration)
      const next = from + (target - from) * (1 - Math.pow(1 - p, 3))
      fromRef.current = next
      setValue(next)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return Number.isFinite(target) ? value : null
}
