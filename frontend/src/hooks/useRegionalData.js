import { useEffect } from 'react'
import { useMarsStore } from '../store/useMarsStore.js'
import { getRegionalFeatures, getRegionalOverview } from '../services/api.js'

// Fetch only regional metadata and Gazetteer labels here. Viewport elevation
// windows are requested by Map2D after Leaflet reports its current bounds.
export function useRegionalData() {
  const region = useMarsStore((s) => s.selectedRegion)

  useEffect(() => {
    if (region.id !== 'regional') return undefined
    let alive = true
    const { setStatus, setResult } = useMarsStore.getState()
    ;(async () => {
      setStatus('regionalFeatures', 'loading')
      const [overview, features] = await Promise.all([getRegionalOverview(), getRegionalFeatures()])
      if (!alive) return
      // Overview metadata accompanies the first viewport result without replacing it.
      setResult('regionalFeatures', features ? { overview, features } : null)
    })()
    return () => { alive = false }
  }, [region.id])
}
