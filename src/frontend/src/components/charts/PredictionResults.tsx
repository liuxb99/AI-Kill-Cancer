import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const accuracyData = [
  { model: 'CNN', accuracy: 94.2, precision: 93.8, recall: 92.5, f1: 93.1 },
  { model: 'ResNet50', accuracy: 96.7, precision: 95.9, recall: 95.2, f1: 95.5 },
  { model: 'ViT', accuracy: 97.1, precision: 96.8, recall: 96.3, f1: 96.5 },
  { model: 'EfficientNet', accuracy: 95.8, precision: 95.1, recall: 94.6, f1: 94.8 },
  { model: 'TransUNet', accuracy: 97.8, precision: 97.3, recall: 97.0, f1: 97.1 },
]

const rocData = [
  { fpr: 0, tpr1: 0, tpr2: 0, tpr3: 0 },
  { fpr: 0.1, tpr1: 0.72, tpr2: 0.68, tpr3: 0.75 },
  { fpr: 0.2, tpr1: 0.85, tpr2: 0.81, tpr3: 0.87 },
  { fpr: 0.3, tpr1: 0.91, tpr2: 0.88, tpr3: 0.93 },
  { fpr: 0.4, tpr1: 0.94, tpr2: 0.92, tpr3: 0.96 },
  { fpr: 0.5, tpr1: 0.96, tpr2: 0.94, tpr3: 0.97 },
  { fpr: 0.6, tpr1: 0.97, tpr2: 0.96, tpr3: 0.98 },
  { fpr: 0.7, tpr1: 0.98, tpr2: 0.97, tpr3: 0.99 },
  { fpr: 0.8, tpr1: 0.99, tpr2: 0.98, tpr3: 0.99 },
  { fpr: 0.9, tpr1: 0.99, tpr2: 0.99, tpr3: 1.0 },
  { fpr: 1.0, tpr1: 1.0, tpr2: 1.0, tpr3: 1.0 },
]

export default function PredictionResults() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">模型效能比較</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={accuracyData} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="model" tick={{ fontSize: 12 }} />
            <YAxis domain={[88, 100]} tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
            />
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
          <LineChart data={rocData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="fpr" tick={{ fontSize: 12 }} label={{ value: '假陽性率', position: 'bottom', fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} label={{ value: '真陽性率', angle: -90, position: 'insideLeft', fontSize: 12 }} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
            />
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
