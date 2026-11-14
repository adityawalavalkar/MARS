import { useCallback, useEffect } from 'react'
import { useMarsStore } from '../store/useMarsStore.js'
import { getMissionReport } from '../services/api.js'

// Fetches the mission report for the current route whenever the modal opens (or on retry).
export function useReport(open) {
  const route = useMarsStore((s) => s.data.route)

  const load = useCallback(async () => {
    const { setStatus, setResult } = useMarsStore.getState()
    setStatus('report', 'loading')
    setResult('report', await getMissionReport(route))
  }, [route])

  useEffect(() => {
    if (open && route) {
      // eslint-disable-next-line no-void
      void load()
    }
  }, [open, route, load])

  return load
}
