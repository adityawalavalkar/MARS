import { useEffect } from 'react'
import { useMarsStore } from '../store/useMarsStore.js'
import { ELEVATION_RESOLUTION } from '../config.js'
import { getComposition, getElevationGrid, getHazardGrid, getMineralRatio, getRadiation, getRegionalGrid, getWeather } from '../services/api.js'

// Loads all region-level data and keeps weather + radiation fresh (poll interval from settings).
export function useRegionData() {
  const region = useMarsStore((s) => s.selectedRegion)
  const refreshSeconds = useMarsStore((s) => s.settings.refreshSeconds)

  useEffect(() => {
    if (region.id !== 'jezero') {
      const { setStatus, setResult } = useMarsStore.getState()
      setStatus('hazard', 'idle')
      if (!region.terrainAvailable) {
        setStatus('elevation', 'idle')
        return undefined
      }
      let alive = true
      setStatus('elevation', 'loading')
      getRegionalGrid(region.bounds, ELEVATION_RESOLUTION).then((overview) => {
        if (!alive) return
        if (!overview?.grid) {
          setResult('elevation', null)
          console.error(`Mars NAV has no regional MOLA elevation grid for ${region.name}.`)
          return
        }
        setResult('elevation', { grid: overview.grid, slope: null, source: overview.source, displayOnly: true })
        const store = useMarsStore.getState()
        store.setViewMode('3d')
        store.setAppPhase('REGION_3D')
      }).catch((error) => {
        if (alive) {
          setResult('elevation', null)
          console.error(`Mars NAV regional terrain load failed for ${region.name}.`, error)
        }
      })
      return () => { alive = false }
    }
    let alive = true
    const { setStatus, setResult } = useMarsStore.getState()
    const load = async (key, fetcher, opts) => {
      setStatus(key, 'loading')
      const result = await fetcher()
      if (alive) setResult(key, result, opts)
    }
    load('hazard', () => getHazardGrid(region.bounds))
    ;(async () => {
      setStatus('elevation', 'loading')
      const elevation = await getElevationGrid(region.bounds, ELEVATION_RESOLUTION)
      if (!alive) return
      setResult('elevation', elevation)
      if (elevation?.grid) {
        const store = useMarsStore.getState()
        store.setViewMode('3d')
        store.setAppPhase('REGION_3D')
      } else {
        console.error(`Mars NAV could not load the Jezero DEM for ${region.name}. Check the backend elevation-grid endpoint and local Jezero raster.`)
      }
    })()
    load('composition', () => getComposition(region))
    load('mineral', () => getMineralRatio(region))
    return () => {
      alive = false
    }
  }, [region])

  useEffect(() => {
    if (region.id !== 'jezero') {
      const { setStatus } = useMarsStore.getState()
      setStatus('weather', 'idle')
      setStatus('radiation', 'idle')
      return undefined
    }
    let alive = true
    const { setStatus, setResult } = useMarsStore.getState()
    const refresh = async (first) => {
      if (first) {
        setStatus('weather', 'loading')
        setStatus('radiation', 'loading')
      }
      const [weather, radiation] = await Promise.all([getWeather(region), getRadiation(region)])
      if (!alive) return
      setResult('weather', weather, { touch: true })
      setResult('radiation', radiation, { touch: true })
    }
    refresh(true)
    const id = setInterval(() => refresh(false), Math.max(10, refreshSeconds) * 1000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [region, refreshSeconds])
}
