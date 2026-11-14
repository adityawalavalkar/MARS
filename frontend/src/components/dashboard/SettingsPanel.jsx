import { useMarsStore } from '../../store/useMarsStore.js'
import { API_BASE_URL, endpoints } from '../../services/api.js'

const STATUS_KEY = {
  weather: 'weather',
  radiation: 'radiation',
  hazardGrid: 'hazard',
  elevationGrid: 'elevation',
  elevationProfile: 'profile',
  composition: 'composition',
  mineralRatio: 'mineral',
  route: 'route',
  missionReport: 'report',
}

export default function SettingsPanel() {
  const settings = useMarsStore((s) => s.settings)
  const status = useMarsStore((s) => s.status)
  const update = useMarsStore((s) => s.updateSettings)

  return (
    <div className="settings glass">
      <h2>Machine settings</h2>
      <div className="settings-grid">
        <label>
          <span>Temperature unit</span>
          <div className="seg seg-mini">
            {['C', 'F'].map((u) => (
              <button key={u} type="button" className={settings.tempUnit === u ? 'on' : ''} onClick={() => update({ tempUnit: u })}>°{u}</button>
            ))}
          </div>
        </label>
        <label>
          <span>Vertical exaggeration · {settings.exaggeration.toFixed(1)}×</span>
          <input type="range" min="1" max="8" step="0.5" value={settings.exaggeration} onChange={(e) => update({ exaggeration: Number(e.target.value) })} />
        </label>
        <label>
          <span>Live data refresh</span>
          <select value={settings.refreshSeconds} onChange={(e) => update({ refreshSeconds: Number(e.target.value) })}>
            {[30, 45, 60].map((s) => (
              <option key={s} value={s}>every {s}s</option>
            ))}
          </select>
        </label>
        <label>
          <span>3D surface overlay</span>
          <select value={settings.overlay3d} onChange={(e) => update({ overlay3d: e.target.value })}>
            <option value="elevation">Elevation</option>
            <option value="hazard">Hazard</option>
            <option value="slope">Slope</option>
          </select>
        </label>
      </div>
      <h3>Backend connection</h3>
      <p className="hint">Base URL: <code>{API_BASE_URL || '(same origin)'}</code></p>
      <ul className="endpoints">
        {Object.entries(endpoints).map(([name, e]) => (
          <li key={name}>
            <i className={`dot dot-${{ ready: 'ok', error: 'err', loading: 'sync', idle: 'idle' }[status[STATUS_KEY[name]]]}`} />
            <b>{e.method}</b> <code>{e.path}</code>
          </li>
        ))}
      </ul>
    </div>
  )
}
