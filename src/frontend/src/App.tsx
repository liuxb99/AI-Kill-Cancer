import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import KnowledgeBase from './pages/KnowledgeBase'
import Tools from './pages/Tools'
import Research from './pages/Research'
import Dashboard from './pages/Dashboard'
import ResearchPortal from './pages/ResearchPortal'
import Workbench from './pages/Workbench'
import RecommendationPage from './pages/RecommendationPage'
import StatusBanner from './components/StatusBanner'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <StatusBanner />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/research" element={<Research />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/research-portal" element={<ResearchPortal />} />
        <Route path="/workbench" element={<Workbench />} />
        <Route path="/recommendation" element={<RecommendationPage />} />
      </Routes>
    </div>
  )
}

export default App
