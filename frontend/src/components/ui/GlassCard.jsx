import { motion } from 'framer-motion'

// status: 'idle' | 'loading' | 'ready' | 'error'. The chip in the header tells the person why a card is empty.
export default function GlassCard({ title, status = 'idle', hasData = false, right, children, className = '' }) {
  let chip = null
  if (status === 'loading' && !hasData) chip = <span className="chip chip-sync">Syncing</span>
  else if (status === 'error' && !hasData) chip = <span className="chip chip-error">Data unavailable</span>
  else if (!hasData) chip = <span className="chip chip-muted">No data yet</span>
  return (
    <motion.section className={`glass ${className}`} whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 24 }}>
      {(title || right || chip) && (
        <header className="glass-head">
          <h3>{title}</h3>
          <div className="glass-right">
            {right}
            {chip}
          </div>
        </header>
      )}
      {children}
    </motion.section>
  )
}
