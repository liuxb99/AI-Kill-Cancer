import { useEffect, useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { getResearchTrends, type ResearchTrendsData } from '../../api/dashboard'

export default function ResearchTrends() {
  const [data, setData] = useState<ResearchTrendsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void getResearchTrends()
      .then((result) => { if (!cancelled) setData(result) })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Failed to load research trends') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) return <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">{[1, 2].map((item) => <div key={item} className="animate-pulse rounded-xl border border-gray-100 bg-white p-6 shadow-sm"><div className="mb-4 h-5 w-40 rounded bg-gray-200" /><div className="h-72 rounded bg-gray-100" /></div>)}</div>
  if (error) return <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-700"><p>無法載入研究趨勢資料</p><p className="mt-1 text-sm">{error}</p></div>
  if (!data) return null

  const { publications, funding } = data
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-gray-800">AI 癌症研究論文發表趨勢</h3>
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={publications}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} /><Legend />
            <Area type="monotone" dataKey="deepLearning" name="深度學習" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} strokeWidth={2} />
            <Area type="monotone" dataKey="genomics" name="基因組學" stroke="#22c55e" fill="#22c55e" fillOpacity={0.15} strokeWidth={2} />
            <Area type="monotone" dataKey="immunotherapy" name="免疫治療" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.15} strokeWidth={2} />
            <Area type="monotone" dataKey="radiomics" name="放射組學" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-gray-800">研究經費投入（十億美元）</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={funding} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} /><Legend />
            <Bar dataKey="government" name="政府經費" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="private" name="私人投資" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
