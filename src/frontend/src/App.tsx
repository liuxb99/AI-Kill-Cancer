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
import StatusBanner from './components/StatusBanner'

function AppNavbar() {
  const navigate = useNavigate()
  const location = useLocation()

  // 只在非首頁顯示導航欄（首頁已有自己的導航）
  if (location.pathname === '/') return null

  const links = [
    { label: '藥物推薦', path: '/recommendation' },
    { label: '臨床決策', path: '/clinical-decision' },
    { label: '知識庫', path: '/knowledge' },
    { label: '工具', path: '/tools' },
    { label: '論文', path: '/research' },
  ]

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 py-2 flex items-center gap-6 text-sm font-medium text-gray-600">
        <span
          className="text-primary-700 font-bold cursor-pointer"
          onClick={() => navigate('/')}
        >
          AI Kill Cancer
        </span>
        <div className="flex gap-4">
          {links.map((link) => (
            <span
              key={link.path}
              className="cursor-pointer hover:text-primary-600 transition"
              onClick={() => navigate(link.path)}
            >
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
        <Route path="/recommendation" element={<RecommendationPage />} />
        <Route path="/clinical-decision" element={<ClinicalDecisionListPage />} />
        <Route path="/clinical-decision/:id" element={<ClinicalDecisionPage />} />
      </Routes>
    </div>
  )
}

export default App
