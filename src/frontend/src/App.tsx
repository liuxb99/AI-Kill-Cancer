import { lazy, Suspense } from 'react'
import { Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import Home from './pages/Home'
import StatusBanner from './components/StatusBanner'

const KnowledgeBase = lazy(() => import('./pages/KnowledgeBase'))
const Tools = lazy(() => import('./pages/Tools'))
const Research = lazy(() => import('./pages/Research'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const ResearchPortal = lazy(() => import('./pages/ResearchPortal'))
const Workbench = lazy(() => import('./pages/Workbench'))
const RecommendationPage = lazy(() => import('./pages/RecommendationPage'))
const ClinicalDecisionPage = lazy(() => import('./pages/ClinicalDecisionPage'))
const ClinicalDecisionListPage = lazy(() => import('./pages/ClinicalDecisionListPage'))
const TumorBoardConsensusListPage = lazy(() => import('./pages/TumorBoardConsensusListPage'))
const TumorBoardConsensusPage = lazy(() => import('./pages/TumorBoardConsensusPage'))
const ClinicalGraphPage = lazy(() => import('./pages/ClinicalGraphPage'))
const TreatmentPlanListPage = lazy(() => import('./pages/TreatmentPlanListPage'))
const TreatmentPlanCreatePage = lazy(() => import('./pages/TreatmentPlanCreatePage'))
const TreatmentPlanDetailPage = lazy(() => import('./pages/TreatmentPlanDetailPage'))
const TreatmentPlanRevisionPage = lazy(() => import('./pages/TreatmentPlanRevisionPage'))
const PTC3DExplorerPage = lazy(() => import('./pages/PTC3DExplorerPage'))
const PTCCohortPage = lazy(() => import('./pages/PTCCohortPage'))
const PTCCommandCenterRoute = lazy(() => import('./pages/PTCCommandCenterRoute'))
const PTCDataQualityPage = lazy(() => import('./pages/PTCDataQualityPage'))
const PTCEvidenceMatrixPage = lazy(() => import('./pages/PTCEvidenceMatrixPage'))
const PTCIntegratedPage = lazy(() => import('./pages/PTCIntegratedPage'))
const PTCKnowledgePage = lazy(() => import('./pages/PTCKnowledgePage'))
const PTCReportCenterPage = lazy(() => import('./pages/PTCReportCenterPage'))
const PTCResearchAssistantPage = lazy(() => import('./pages/PTCResearchAssistantPage'))
const PTCResearchDepthPage = lazy(() => import('./pages/PTCResearchDepthPage'))
const PTCResearchPage = lazy(() => import('./pages/PTCResearchPage'))
const PTCSnapshotPage = lazy(() => import('./pages/PTCSnapshotPage'))
const PTCTimelinePage = lazy(() => import('./pages/PTCTimelinePage'))
const PTCTrialMatchingPage = lazy(() => import('./pages/PTCTrialMatchingPage'))
const ProductionReadinessPage = lazy(() => import('./pages/ProductionReadinessPage'))
const WorkspaceImportPage = lazy(() => import('./pages/WorkspaceImportPage'))

function AppNavbar() {
  const navigate = useNavigate()
  const location = useLocation()
  if (location.pathname === '/') return null

  const params = new URLSearchParams(location.search)
  const demoCase = params.get('demo_case')
  const synthetic = params.get('data_mode') === 'synthetic' || Boolean(demoCase)
  const demoSearch = synthetic && demoCase
    ? `?demo_case=${encodeURIComponent(demoCase)}&data_mode=synthetic`
    : ''
  const navigateWithContext = (path: string) => navigate(`${path}${demoSearch}`)

  const links = [
    { label: '生产就绪', path: '/production-readiness' },
    { label: 'Workspace 匯入', path: '/workspace-import' },
    { label: 'PTC 總控台', path: '/ptc-command-center' },
    { label: 'PTC 資料品質', path: '/ptc-data-quality' },
    { label: 'PTC 研究深度', path: '/ptc-research-depth' },
    { label: 'PTC 研究快照', path: '/ptc-snapshots' },
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
        <span className="text-primary-700 font-bold cursor-pointer whitespace-nowrap" onClick={() => navigateWithContext('/')}>
          AI Kill Cancer
        </span>
        <div className="flex gap-4 whitespace-nowrap">
          {links.map((link) => (
            <span key={link.path} className="cursor-pointer hover:text-primary-600 transition" onClick={() => navigateWithContext(link.path)}>
              {link.label}
            </span>
          ))}
        </div>
      </div>
    </nav>
  )
}

function RouteFallback() {
  return (
    <div className="min-h-[50vh] flex items-center justify-center text-sm text-gray-500">
      功能載入中…
    </div>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <StatusBanner />
      <AppNavbar />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/research" element={<Research />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/research-portal" element={<ResearchPortal />} />
          <Route path="/workbench" element={<Workbench />} />
          <Route path="/production-readiness" element={<ProductionReadinessPage />} />
          <Route path="/workspace-import" element={<WorkspaceImportPage />} />
          <Route path="/ptc-command-center" element={<PTCCommandCenterRoute />} />
          <Route path="/ptc-data-quality" element={<PTCDataQualityPage />} />
          <Route path="/ptc-research-depth" element={<PTCResearchDepthPage />} />
          <Route path="/ptc-snapshots" element={<PTCSnapshotPage />} />
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
      </Suspense>
    </div>
  )
}

export default App