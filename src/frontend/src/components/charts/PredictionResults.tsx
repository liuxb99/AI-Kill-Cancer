import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { getPredictionResults, type PredictionResultsData } from '../../api/dashboard'

export default function PredictionResults() {
  const [data, setData] = useState<PredictionResultsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void getPredictionResults()
      .then((result) => { if (!cancelled) setData(result) })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Failed to load prediction results') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) return <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">{[1, 2].map((item) => <div key={item} className="animate-pulse rounded-xl border border-gray-100 bg-white p-6 shadow-sm"><div className="mb-4 h-5 w-40 rounded bg-gray-200" /><div className="h-72 rounded bg-gray-100" /></div>)}</div>
  if (error) return <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-700"><p>無法載入預測結果資料</p><p className="mt-1 text-sm">{error}</p></div>
  if (!data) return null

  const { accuracy, roc } = data
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-gray-800">模型效能比較</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={accuracy} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="model" tick={{ fontSize: 12 }} /><YAxis domain={[88, 100]} tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} /><Legend />
            <Bar dataKey="accuracy" name="準確率 %" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="precision" name="精確率 %" fill="#22c55e" radius={[4, 4, 0, 0]} />
            <Bar dataKey="recall" name="召回率 %" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            <Bar dataKey="f1" name="F1 分數 %" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-gray-800">ROC 曲線</h3>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={roc}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="fpr" tick={{ fontSize: 12 }} label={{ value: '假陽性率', position: 'bottom', fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} label={{ value: '真陽性率', angle: -90, position: 'insideLeft', fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }} /><Legend />
            <Line type="monotone" dataKey="tpr1" name="CNN (AUC=0.94)" stroke="#6366f1" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="tpr2" name="ResNet50 (AUC=0.96)" stroke="#22c55e" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="tpr3" name="TransUNet (AUC=0.98)" stroke="#ef4444" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
