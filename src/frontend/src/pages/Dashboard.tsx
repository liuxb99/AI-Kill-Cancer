import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboardKPIs, type DashboardKPI } from '../api/dashboard'
import CancerStats from '../components/charts/CancerStats'
import PredictionResults from '../components/charts/PredictionResults'
import ResearchTrends from '../components/charts/ResearchTrends'

export default function Dashboard() {
  const navigate = useNavigate()
  const [kpis, setKpis] = useState<DashboardKPI[] | null>(null)
  const [kpiLoading, setKpiLoading] = useState(true)
  const [kpiError, setKpiError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setKpiLoading(true)
    setKpiError(null)

    void getDashboardKPIs()
      .then((result) => {
        if (!cancelled) setKpis(result.kpis)
      })
      .catch((reason) => {
        if (!cancelled) setKpiError(reason instanceof Error ? reason.message : 'Failed to load KPIs')
      })
      .finally(() => {
        if (!cancelled) setKpiLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  const defaultKpis: DashboardKPI[] = [
    { label: '涵蓋癌症種類（模擬）', value: '12', unit: '種' },
    { label: 'AI 模型準確率（模擬）', value: '97.8', unit: '%' },
    { label: '研究論文數（模擬）', value: '8,640', unit: '篇' },
    { label: '臨床試驗（模擬）', value: '342', unit: '項' },
  ]

  const displayKpis = kpis ?? defaultKpis

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')} className="text-sm text-gray-500 transition hover:text-primary-600">&larr; 回首頁</button>
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

      <main className="mx-auto flex-1 max-w-7xl space-y-8 px-4 py-8">
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
          ⓘ 此儀表板可能包含<strong>模擬資料</strong>，僅供展示用途，不可用於診斷或治療決策。
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {kpiLoading
            ? [1, 2, 3, 4].map((item) => (
                <div key={item} className="animate-pulse rounded-xl border border-gray-100 bg-white p-5 text-center shadow-sm">
                  <div className="mx-auto mb-2 h-8 w-20 rounded bg-gray-200" />
                  <div className="mx-auto h-4 w-16 rounded bg-gray-100" />
                </div>
              ))
            : displayKpis.map((kpi) => (
                <div key={kpi.label} className="rounded-xl border border-gray-100 bg-white p-5 text-center shadow-sm">
                  <p className="text-3xl font-bold text-primary-600">{kpi.value}<span className="ml-1 text-sm font-normal text-gray-400">{kpi.unit}</span></p>
                  <p className="mt-1 text-sm text-gray-500">{kpi.label}</p>
                </div>
              ))}
        </div>

        {kpiError && <div className="text-center text-xs text-amber-600">無法從 API 取得 KPI，顯示預設資料（{kpiError}）</div>}

        <section><h2 className="mb-4 text-lg font-semibold text-gray-800">癌症統計</h2><CancerStats /></section>
        <section><h2 className="mb-4 text-lg font-semibold text-gray-800">模型預測結果</h2><PredictionResults /></section>
        <section><h2 className="mb-4 text-lg font-semibold text-gray-800">研究趨勢分析</h2><ResearchTrends /></section>
      </main>

      <footer className="border-t border-gray-200 bg-gray-100 py-6 text-center text-sm text-gray-500">AI Kill Cancer Dashboard &copy; 2026</footer>
    </div>
  )
}
