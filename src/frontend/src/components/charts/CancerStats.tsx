import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'

const incidenceData = [
  { name: '肺癌', male: 58.2, female: 32.4 },
  { name: '乳癌', male: 0.5, female: 88.2 },
  { name: '大腸癌', male: 42.3, female: 32.1 },
  { name: '肝癌', male: 38.7, female: 15.2 },
  { name: '胃癌', male: 28.1, female: 14.3 },
  { name: '攝護腺癌', male: 45.6, female: 0 },
  { name: '甲狀腺癌', male: 8.5, female: 24.6 },
]

const mortalityData = [
  { name: '肺癌', value: 38 },
  { name: '肝癌', value: 22 },
  { name: '大腸癌', value: 18 },
  { name: '胃癌', value: 13 },
  { name: '乳癌', value: 9 },
]

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']

export default function CancerStats() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">癌症發生率（每 10 萬人）</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={incidenceData} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
            />
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
              data={mortalityData}
              cx="50%"
              cy="50%"
              labelLine
              label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
              outerRadius={110}
              innerRadius={50}
              dataKey="value"
            >
              {mortalityData.map((_, idx) => (
                <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
