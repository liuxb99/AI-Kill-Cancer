import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CancerStats from '../components/charts/CancerStats'
import PredictionResults from '../components/charts/PredictionResults'
import ResearchTrends from '../components/charts/ResearchTrends'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface KPI {
  label: string
  value: string
  unit: string
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [kpis, setKpis] = useState<KPI[] | null>(null)
  const [kpiLoading, setKpiLoading] = useState(true)
  const [kpiError, setKpiError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setKpiLoading(true)
    setKpiError(null)

    fetch(`${API_BASE}/api/v1/dashboard/kpis`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((res) => {
        if (!cancelled) setKpis(res.kpis)
      })
      .catch((e) => {
        if (!cancelled) setKpiError(e.message || 'Failed to load KPIs')
      })
      .finally(() => {
        if (!cancelled) setKpiLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  const defaultKpis: KPI[] = [
    { label: '涵蓋癌症種類 (模擬)', value: '12', unit: '種' },
    { label: 'AI 模型準確率 (模擬)', value: '97.8', unit: '%' },
    { label: '研究論文數 (模擬)', value: '8,640', unit: '篇' },
    { label: '臨床試驗 (模擬)', value: '342', unit: '項' },
  ]

  const displayKpis = kpis ?? defaultKpis

  return (
    <div className="flex flex-col min-h-screen">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="text-sm text-gray-500 hover:text-primary-600 transition"
            >
              &larr; 回首頁
            </button>
            <h1 className="text-xl font-bold text-primary-700">數據儀表板</h1>
          </div>
          <nav className="flex gap-6 text-sm font-medium text-gray-600">
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/recommendation')}>藥物推薦</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/knowledge')}>知識庫</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/tools')}>工具</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/research')}>論文</span>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 py-8 space-y-8">
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-800">
          ⓘ 此儀表板顯示<strong>模擬數據</strong>，僅供展示用途，不可用於診斷或治療決策。
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {kpiLoading
            ? [1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 text-center animate-pulse">
                  <div className="h-8 w-20 bg-gray-200 rounded mx-auto mb-2" />
                  <div className="h-4 w-16 bg-gray-100 rounded mx-auto" />
                </div>
              ))
            : displayKpis.map((kpi) => (
                <div
                  key={kpi.label}
                  className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 text-center"
                >
                  <p className="text-3xl font-bold text-primary-600">
                    {kpi.value}
                    <span className="text-sm font-normal text-gray-400 ml-1">{kpi.unit}</span>
                  </p>
                  <p className="text-sm text-gray-500 mt-1">{kpi.label}</p>
                </div>
              ))}
        </div>
        {kpiError && (
          <div className="text-xs text-center text-amber-600">
            無法從 API 取得 KPI 數據，使用預設值（{kpiError}）
          </div>
        )}

        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">癌症統計</h2>
          <CancerStats />
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">模型預測結果</h2>
          <PredictionResults />
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">研究趨勢分析</h2>
          <ResearchTrends />
        </section>
      </main>

      <footer className="bg-gray-100 border-t border-gray-200 py-6 text-center text-sm text-gray-500">
        AI Kill Cancer Dashboard &copy; 2026
      </footer>
    </div>
  )
}
