import { motion } from 'framer-motion'
import { useMarsStore } from '../../store/useMarsStore.js'
import { LAYERS, getLayerGrid, layerById, layerRange } from '../../utils/layers.js'
import { cssGradient } from '../../utils/colors.js'
import { fmt } from '../../utils/format.js'

export default function LayerSwitcher() {
  const activeLayer = useMarsStore((s) => s.activeLayer)
  const setLayer = useMarsStore((s) => s.setLayer)
  const opacity = useMarsStore((s) => s.layerOpacity)
  const setOpacity = useMarsStore((s) => s.setOpacity)
  const data = useMarsStore((s) => s.data)
  const layer = layerById(activeLayer)
  const grid = getLayerGrid(activeLayer, data)
  const [lo, hi] = layerRange(layer, grid)
  const digits = hi - lo < 10 ? 2 : 0

  return (
    <div className="layer-switcher glass">
      <div className="seg seg-wrap" role="tablist" aria-label="Map layer">
        {LAYERS.map((l) => (
          <button key={l.id} type="button" role="tab" aria-selected={activeLayer === l.id} className={activeLayer === l.id ? 'on' : ''} onClick={() => setLayer(l.id)}>
            {activeLayer === l.id && <motion.span layoutId="layer-pill" className="seg-pill" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
            <span>{l.label}</span>
          </button>
        ))}
      </div>
      <label className="opacity">
        <span>Opacity</span>
        <input type="range" min="0.1" max="1" step="0.05" value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
      </label>
      <div className="legend-bar">
        <div className="legend-grad" style={{ background: cssGradient(layer.ramp), opacity: grid ? 1 : 0.35 }} />
        <div className="legend-ends">
          <span>{grid ? `${fmt(lo, digits)} ${layer.unit}` : '—'}</span>
          <span>{grid ? `${fmt(hi, digits)} ${layer.unit}` : 'No data yet'}</span>
        </div>
      </div>
    </div>
  )
}
