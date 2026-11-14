import { useEffect, useState } from 'react'

export function useSecondsAgo(timestamp) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  return timestamp ? Math.max(0, Math.round((now - timestamp) / 1000)) : null
}
