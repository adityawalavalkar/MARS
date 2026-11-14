import { motion } from 'framer-motion'
import { useMarsStore } from '../../store/useMarsStore.js'

export default function ViewToggle() {
  const viewMode = useMarsStore((s) => s.viewMode)
  const setViewMode = useMarsStore((s) => s.setViewMode)
  return (
    <div className="view-toggle" role="group" aria-label="View mode">
      {['3d', '2d'].map((m) => (
        <button key={m} type="button" className={viewMode === m ? 'on' : ''} onClick={() => setViewMode(m)}>
          {viewMode === m && <motion.span layoutId="vt-pill" className="vt-pill" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
          <span>{m.toUpperCase()}</span>
        </button>
      ))}
    </div>
  )
}
