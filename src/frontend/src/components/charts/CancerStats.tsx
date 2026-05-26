import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface CancerStatsData {
  incidence: { name: string; male: number; female: number }[]
  mortality: { name: string; value: number }[]
  mortality_colors: string[]
}

export default function CancerStats() {
  const [data, setData] = useState<CancerStatsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(`${API_BASE}/api/v1/charts/cancer-stats`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || 'Failed to load cancer stats')
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
        <p>無法載入癌症統計數據</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    )
  }

  if (!data) return null

  const { incidence, mortality, mortality_colors } = data

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">癌症發生率（每 10 萬人）</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={incidence} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} />
            <Legend />
            <Bar dataKey="male" name="男性" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="female" name="女性" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">主要癌症死亡率佔比</h3>
        <ResponsiveContainer width="100%" height={320}>
          <PieChart>
            <Pie
              data={mortality}
              cx="50%"
              cy="50%"
              labelLine
              label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
              outerRadius={110}
              innerRadius={50}
              dataKey="value"
            >
              {mortality.map((_, idx) => (
                <Cell key={idx} fill={mortality_colors[idx % mortality_colors.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
