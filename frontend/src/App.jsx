import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { SESSION_INTRO_KEY } from './config.js'
import { useMarsStore } from './store/useMarsStore.js'

const loadDashboard = () => import('./components/dashboard/Dashboard.jsx')
const Dashboard = lazy(loadDashboard)
const IntroScene = lazy(() => import('./components/intro/IntroScene.jsx'))

function introAlreadySeen() {
  try {
    return sessionStorage.getItem(SESSION_INTRO_KEY) === '1'
  } catch {
    return false
  }
}

export default function App() {
  const [phase, setPhase] = useState(() => (introAlreadySeen() ? 'dashboard' : 'intro'))
  const setAppPhase = useMarsStore((s) => s.setAppPhase)

  useEffect(() => { setAppPhase(phase === 'intro' ? 'INTRO' : 'MAP') }, [phase, setAppPhase])

  useEffect(() => {
    if (phase === 'intro') loadDashboard().catch(() => {})
  }, [phase])

  const finishIntro = useCallback(() => {
    try {
      sessionStorage.setItem(SESSION_INTRO_KEY, '1')
    } catch {
      /* storage unavailable: intro simply plays again next session */
    }
    setPhase('dashboard')
    setAppPhase('MAP')
  }, [setAppPhase])

  return (
    <>
      <Suspense fallback={<div className="boot" />}>{phase === 'dashboard' && <Dashboard />}</Suspense>
      <AnimatePresence>
        {phase === 'intro' && (
          <motion.div key="intro" className="intro-layer" exit={{ opacity: 0 }} transition={{ duration: 1.1, ease: 'easeInOut' }}>
            <Suspense fallback={<div className="boot" />}>
              <IntroScene onDone={finishIntro} />
            </Suspense>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
