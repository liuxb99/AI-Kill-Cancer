import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import { getCancerStats, type CancerStatsData } from '../../api/dashboard'

export default function CancerStats() {
  const [data, setData] = useState<CancerStatsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void getCancerStats()
      .then((result) => { if (!cancelled) setData(result) })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Failed to load cancer stats') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">{[1, 2].map((item) => <div key={item} className="animate-pulse rounded-xl border border-gray-100 bg-white p-6 shadow-sm"><div className="mb-4 h-5 w-40 rounded bg-gray-200" /><div className="h-72 rounded bg-gray-100" /></div>)}</div>
  }
  if (error) return <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-700"><p>無法載入癌症統計資料</p><p className="mt-1 text-sm">{error}</p></div>
  if (!data) return null

  const { incidence, mortality, mortality_colors } = data
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-gray-800">癌症發生率（每 10 萬人）</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={incidence} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} /><Legend />
            <Bar dataKey="male" name="男性" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="female" name="女性" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-gray-800">主要癌症死亡率占比</h3>
        <ResponsiveContainer width="100%" height={320}>
          <PieChart>
            <Pie data={mortality} cx="50%" cy="50%" labelLine label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} outerRadius={110} innerRadius={50} dataKey="value">
              {mortality.map((_, index) => <Cell key={index} fill={mortality_colors[index % mortality_colors.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
