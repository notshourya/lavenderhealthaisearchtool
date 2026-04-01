import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import RunsPage from './pages/RunsPage'
import ClinicsPage from './pages/ClinicsPage'
import ClinicDetailPage from './pages/ClinicDetailPage'
import DraftsPage from './pages/DraftsPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/runs" replace />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/clinics" element={<ClinicsPage />} />
        <Route path="/clinics/:id" element={<ClinicDetailPage />} />
        <Route path="/drafts" element={<DraftsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}
