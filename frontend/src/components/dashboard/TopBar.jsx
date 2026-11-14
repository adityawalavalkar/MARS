import { useMarsStore } from '../../store/useMarsStore.js'
import { useSecondsAgo } from '../../hooks/useSecondsAgo.js'

export default function TopBar() {
  const lastUpdated = useMarsStore((s) => s.lastUpdated)
  const status = useMarsStore((s) => s.status)
  const ago = useSecondsAgo(lastUpdated)

  const live = ['weather', 'radiation'].map((k) => status[k])
  const dot = live.includes('loading') && !lastUpdated ? 'sync' : live.some((s) => s === 'ready') ? 'ok' : live.every((s) => s === 'error') ? 'err' : 'idle'

  return (
    <header className="topbar">
      <div className="logo">
        <span className="logo-mark" aria-hidden="true" />
        <span>MARS NAV</span>
      </div>
      <div className="tabs-hint">Select the Jezero Crater</div>
      <div className="topbar-right">
        <span className="upd">UPD: {ago === null ? '—' : `${ago}s ago`}</span>
        <span className={`dot dot-${dot}`} title={`Backend: ${dot}`} />
        <span className="avatar" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" />
          </svg>
        </span>
      </div>
    </header>
  )
}
