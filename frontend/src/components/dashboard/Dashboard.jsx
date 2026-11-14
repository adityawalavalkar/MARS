import { AnimatePresence, motion } from 'framer-motion'
import { useMarsStore } from '../../store/useMarsStore.js'
import { useRegionData } from '../../hooks/useRegionData.js'
import { useRouteData } from '../../hooks/useRouteData.js'
import { useRegionalData } from '../../hooks/useRegionalData.js'
import TopBar from './TopBar.jsx'
import CenterView from './CenterView.jsx'
import ReportModal from '../panels/ReportModal.jsx'
import JezeroDashboard from '../../jezero/JezeroDashboard.jsx'

const ease = [0.22, 1, 0.36, 1]

function LegacyDashboard() {
  useRegionData()
  useRegionalData()
  useRouteData()
  const reportOpen = useMarsStore((s) => s.reportOpen)

  return (
    <div className="dash">
      <TopBar />
      <main className="dash-main">
        <motion.section className="center center-full" initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.8, delay: 0.05, ease }}>
          <CenterView />
        </motion.section>
      </main>
      <AnimatePresence>{reportOpen && <ReportModal key="report" />}</AnimatePresence>
    </div>
  )
}

export default function Dashboard() {
  const regionId = useMarsStore((s) => s.selectedRegion.id)
  return regionId === 'jezero' ? <JezeroDashboard /> : <LegacyDashboard />
}
