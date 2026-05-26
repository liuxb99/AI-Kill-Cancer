import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface PredictionResultsData {
  accuracy: { model: string; accuracy: number; precision: number; recall: number; f1: number }[]
  roc: { fpr: number; tpr1: number; tpr2: number; tpr3: number }[]
}

export default function PredictionResults() {
  const [data, setData] = useState<PredictionResultsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(`${API_BASE}/api/v1/charts/prediction-results`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || 'Failed to load prediction results')
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
        <p>無法載入預測結果數據</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    )
  }

  if (!data) return null

  const { accuracy, roc } = data

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">模型效能比較</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={accuracy} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="model" tick={{ fontSize: 12 }} />
            <YAxis domain={[88, 100]} tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} />
            <Legend />
            <Bar dataKey="accuracy" name="準確率 %" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="precision" name="精確率 %" fill="#22c55e" radius={[4, 4, 0, 0]} />
            <Bar dataKey="recall" name="召回率 %" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            <Bar dataKey="f1" name="F1 分數 %" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">ROC 曲線</h3>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={roc}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="fpr" tick={{ fontSize: 12 }} label={{ value: '假陽性率', position: 'bottom', fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} label={{ value: '真陽性率', angle: -90, position: 'insideLeft', fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} />
            <Legend />
            <Line type="monotone" dataKey="tpr1" name="CNN (AUC=0.94)" stroke="#6366f1" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="tpr2" name="ResNet50 (AUC=0.96)" stroke="#22c55e" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="tpr3" name="TransUNet (AUC=0.98)" stroke="#ef4444" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
