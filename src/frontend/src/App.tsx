import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import KnowledgeBase from './pages/KnowledgeBase'
import Tools from './pages/Tools'
import Research from './pages/Research'
import Dashboard from './pages/Dashboard'
import ResearchPortal from './pages/ResearchPortal'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/research" element={<Research />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/research-portal" element={<ResearchPortal />} />
      </Routes>
    </div>
  )
}

export default App
