import { API_BASE_URL } from '../services/api.js'
const j = async (url, opt) => {
  try {
    const r = await fetch(`${API_BASE_URL}${url}`, opt)
    if (!r.ok) return { error: true, detail: `HTTP ${r.status}` }
    return await r.json()
  } catch (e) { return { error: true, detail: `Backend unreachable (${e.message}). Start it with: python run_backend.py` } }
}
export const getJezeroConfig = () => j('/api/jezero/config')
export const planJezero = (body) => j('/api/jezero/route', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const getPov = (lat, lon) => j(`/api/jezero/pov?lat=${lat}&lon=${lon}&radius_m=1600`)
export const getStatic = async (path) => { try { const r = await fetch(path); return r.ok ? await r.json() : null } catch { return null } }
