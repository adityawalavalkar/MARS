import { useEffect } from 'react'
import { useMarsStore } from '../store/useMarsStore.js'
import { getElevationProfile, getRoute } from '../services/api.js'
import { calculateMarsTraverse } from '../utils/marsCalculations.js'

// When both START and END exist, fetch the route and then its elevation profile.
export function useRouteData() {
  const start = useMarsStore((s) => s.start)
  const end = useMarsStore((s) => s.end)
  const missionMode = useMarsStore((s) => s.missionMode)
  const safetyWeight = useMarsStore((s) => s.safetyWeight)
  const crewSize = useMarsStore((s) => s.crewSize)
  const roverSpeedKmh = useMarsStore((s) => s.roverSpeedKmh)
  const calculationRequested = useMarsStore((s) => s.calculationRequested)

  useEffect(() => {
    if (!start || !end || !calculationRequested) return undefined
    let alive = true
    const { setStatus, setResult } = useMarsStore.getState()
    ;(async () => {
      setStatus('route', 'loading')
      setStatus('profile', 'idle')
      const route = await getRoute(start, end, { mode: missionMode, safety_weight: safetyWeight, max_slope_limit: 25, crew_size: crewSize })
      if (!alive) return
      setResult('route', route)
      if (!route) {
        console.error('Mars NAV route calculation failed. Verify the route endpoint and Jezero data bounds.')
        useMarsStore.getState().requestCalculation(false)
        return
      }
      setStatus('profile', 'loading')
      const profile = await getElevationProfile(route)
      if (alive) {
        setResult('profile', profile)
        if (profile) {
          try {
            setResult('calculation', calculateMarsTraverse({ start, end, profile, speedKmh: roverSpeedKmh }))
            useMarsStore.getState().setAppPhase('RESULTS')
          } catch (error) {
            console.error('Mars NAV could not calculate the DEM-based traverse metrics.', error)
            setResult('calculation', { error: true, detail: error.message })
          }
        } else console.error('Mars NAV returned no usable elevation profile for the selected traverse.')
        if (!profile) useMarsStore.getState().requestCalculation(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [start, end, missionMode, safetyWeight, crewSize, roverSpeedKmh, calculationRequested])
}
