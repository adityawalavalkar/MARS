import { useEffect, useRef } from 'react'

const STAGES = [
  'Initializing navigation systems…',
  'Calibrating star trackers…',
  'Acquiring orbital telemetry…',
  'Entering Martian atmosphere…',
]

// DOM overlay: title, subtitle, progress bar and the final vignette/motion-blur — all driven by the shared timeline ref.
export default function LoadingOverlay({ tl, stageRef, failed, onSkip }) {
  const bar = useRef(null)
  const pct = useRef(null)
  const sub = useRef(null)
  const title = useRef(null)
  const vignette = useRef(null)

  useEffect(() => {
    let raf
    const loop = () => {
      const { progress, t, zoom } = tl.current
      const p = Math.min(1, progress)
      if (bar.current) bar.current.style.transform = `scaleX(${p})`
      if (pct.current) pct.current.textContent = `${Math.round(p * 100)}%`
      if (sub.current) {
        const text = STAGES[Math.min(STAGES.length - 1, Math.floor(p * STAGES.length))]
        if (sub.current.textContent !== text) sub.current.textContent = text
      }
      if (title.current) {
        const pulse = t > 2 && t < 5 ? 0.5 + 0.5 * Math.sin(t * 5) : 0
        title.current.style.setProperty('--glow', String(0.35 + 0.55 * pulse + 0.4 * zoom))
        title.current.style.opacity = String(1 - zoom)
      }
      if (vignette.current) vignette.current.style.opacity = String(Math.pow(zoom, 1.5))
      if (stageRef.current) stageRef.current.style.filter = zoom > 0.02 ? `blur(${(zoom * 5).toFixed(2)}px) saturate(${1 + zoom * 0.3})` : 'none'
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [tl, stageRef])

  return (
    <div className="intro-overlay">
      <div className="intro-head" ref={title}>
        <h1 className="intro-title">MARS NAV</h1>
        <p className="intro-sub" ref={sub}>
          {STAGES[0]}
        </p>
      </div>
      <div className="intro-foot">
        <div className="intro-bar">
          <div className="intro-bar-fill" ref={bar} />
        </div>
        <span className="intro-pct" ref={pct}>
          0%
        </span>
        {failed && <span className="intro-warn">Texture unavailable — using fallback surface</span>}
      </div>
      <button className="intro-skip" onClick={onSkip} type="button">
        Skip intro
      </button>
      <div className="intro-vignette" ref={vignette} />
    </div>
  )
}
