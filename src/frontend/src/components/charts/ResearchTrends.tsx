import { useEffect, useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface ResearchTrendsData {
  publications: { year: string; deepLearning: number; genomics: number; immunotherapy: number; radiomics: number }[]
  funding: { year: string; government: number; private: number }[]
}

export default function ResearchTrends() {
  const [data, setData] = useState<ResearchTrendsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(`${API_BASE}/api/v1/charts/research-trends`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || 'Failed to load research trends')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2].map((i) => (
          <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 animate-pulse">
            <div className="h-5 w-40 bg-gray-200 rounded mb-4" />
            <div className="h-72 bg-gray-100 rounded" />
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-700">
        <p>無法載入研究趨勢數據</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    )
  }

  if (!data) return null

  const { publications, funding } = data

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">AI 癌症研究論文發表趨勢</h3>
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={publications}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} />
            <Legend />
            <Area type="monotone" dataKey="deepLearning" name="深度學習" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} strokeWidth={2} />
            <Area type="monotone" dataKey="genomics" name="基因組學" stroke="#22c55e" fill="#22c55e" fillOpacity={0.15} strokeWidth={2} />
            <Area type="monotone" dataKey="immunotherapy" name="免疫治療" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.15} strokeWidth={2} />
            <Area type="monotone" dataKey="radiomics" name="放射組學" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">研究經費投入（十億美元）</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={funding} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} />
            <Legend />
            <Bar dataKey="government" name="政府經費" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="private" name="私人投資" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
