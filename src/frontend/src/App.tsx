import { Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import Home from './pages/Home'
import KnowledgeBase from './pages/KnowledgeBase'
import Tools from './pages/Tools'
import Research from './pages/Research'
import Dashboard from './pages/Dashboard'
import ResearchPortal from './pages/ResearchPortal'
import Workbench from './pages/Workbench'
import RecommendationPage from './pages/RecommendationPage'
import ClinicalDecisionPage from './pages/ClinicalDecisionPage'
import ClinicalDecisionListPage from './pages/ClinicalDecisionListPage'
import TumorBoardConsensusListPage from './pages/TumorBoardConsensusListPage'
import TumorBoardConsensusPage from './pages/TumorBoardConsensusPage'
import ClinicalGraphPage from './pages/ClinicalGraphPage'
import TreatmentPlanListPage from './pages/TreatmentPlanListPage'
import TreatmentPlanCreatePage from './pages/TreatmentPlanCreatePage'
import TreatmentPlanDetailPage from './pages/TreatmentPlanDetailPage'
import TreatmentPlanRevisionPage from './pages/TreatmentPlanRevisionPage'
import PTC3DExplorerPage from './pages/PTC3DExplorerPage'
import PTCCohortPage from './pages/PTCCohortPage'
import PTCCommandCenterPage from './pages/PTCCommandCenterPage'
import PTCDataQualityPage from './pages/PTCDataQualityPage'
import PTCEvidenceMatrixPage from './pages/PTCEvidenceMatrixPage'
import PTCIntegratedPage from './pages/PTCIntegratedPage'
import PTCKnowledgePage from './pages/PTCKnowledgePage'
import PTCReportCenterPage from './pages/PTCReportCenterPage'
import PTCResearchAssistantPage from './pages/PTCResearchAssistantPage'
import PTCResearchPage from './pages/PTCResearchPage'
import PTCTimelinePage from './pages/PTCTimelinePage'
import PTCTrialMatchingPage from './pages/PTCTrialMatchingPage'
import StatusBanner from './components/StatusBanner'

function AppNavbar() {
  const navigate = useNavigate()
  const location = useLocation()
  if (location.pathname === '/') return null

  const links = [
    { label: 'PTC 總控台', path: '/ptc-command-center' },
    { label: 'PTC 資料品質', path: '/ptc-data-quality' },
    { label: 'PTC 3D', path: '/ptc-3d' },
    { label: 'PTC Digital Thread', path: '/ptc-timeline' },
    { label: 'PTC 試驗比對', path: '/ptc-trial-matching' },
    { label: 'PTC 證據矩陣', path: '/ptc-evidence-matrix' },
    { label: 'PTC 相似隊列', path: '/ptc-cohort' },
    { label: 'PTC 研究助手', path: '/ptc-assistant' },
    { label: 'PTC 研究報告', path: '/ptc-reports' },
    { label: 'PTC 工作台', path: '/ptc-workbench' },
    { label: 'PTC 病例', path: '/ptc-research' },
    { label: 'PTC 藥物證據', path: '/ptc-knowledge' },
    { label: '藥物推薦', path: '/recommendation' },
    { label: '臨床決策', path: '/clinical-decision' },
    { label: '腫瘤委員會', path: '/tumor-board' },
    { label: '知識庫', path: '/knowledge' },
    { label: '工具', path: '/tools' },
    { label: '論文', path: '/research' },
    { label: '知識圖譜', path: '/clinical-graph' },
  ]

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-2 flex items-center gap-6 text-sm font-medium text-gray-600 overflow-x-auto">
        <span className="text-primary-700 font-bold cursor-pointer whitespace-nowrap" onClick={() => navigate('/')}>
          AI Kill Cancer
        </span>
        <div className="flex gap-4 whitespace-nowrap">
          {links.map((link) => (
            <span key={link.path} className="cursor-pointer hover:text-primary-600 transition" onClick={() => navigate(link.path)}>
              {link.label}
            </span>
          ))}
        </div>
      </div>
    </nav>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <StatusBanner />
      <AppNavbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/research" element={<Research />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/research-portal" element={<ResearchPortal />} />
        <Route path="/workbench" element={<Workbench />} />
        <Route path="/ptc-command-center" element={<PTCCommandCenterPage />} />
        <Route path="/ptc-data-quality" element={<PTCDataQualityPage />} />
        <Route path="/ptc-3d" element={<PTC3DExplorerPage />} />
        <Route path="/ptc-timeline" element={<PTCTimelinePage />} />
        <Route path="/ptc-trial-matching" element={<PTCTrialMatchingPage />} />
        <Route path="/ptc-evidence-matrix" element={<PTCEvidenceMatrixPage />} />
        <Route path="/ptc-cohort" element={<PTCCohortPage />} />
        <Route path="/ptc-assistant" element={<PTCResearchAssistantPage />} />
        <Route path="/ptc-reports" element={<PTCReportCenterPage />} />
        <Route path="/ptc-workbench" element={<PTCIntegratedPage />} />
        <Route path="/ptc-research" element={<PTCResearchPage />} />
        <Route path="/ptc-knowledge" element={<PTCKnowledgePage />} />
        <Route path="/recommendation" element={<RecommendationPage />} />
        <Route path="/clinical-decision" element={<ClinicalDecisionListPage />} />
        <Route path="/clinical-decision/:id" element={<ClinicalDecisionPage />} />
        <Route path="/tumor-board" element={<TumorBoardConsensusListPage />} />
        <Route path="/tumor-board/:id" element={<TumorBoardConsensusPage />} />
        <Route path="/clinical-graph" element={<ClinicalGraphPage />} />
        <Route path="/treatment-plans" element={<TreatmentPlanListPage />} />
        <Route path="/treatment-plans/new" element={<TreatmentPlanCreatePage />} />
        <Route path="/treatment-plans/:id" element={<TreatmentPlanDetailPage />} />
        <Route path="/treatment-plans/:id/revise" element={<TreatmentPlanRevisionPage />} />
      </Routes>
    </div>
  )
}

export default App
