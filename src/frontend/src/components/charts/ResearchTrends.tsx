import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const publicationsData = [
  { year: '2016', deepLearning: 120, genomics: 340, immunotherapy: 280, radiomics: 90 },
  { year: '2017', deepLearning: 210, genomics: 390, immunotherapy: 350, radiomics: 140 },
  { year: '2018', deepLearning: 380, genomics: 420, immunotherapy: 440, radiomics: 210 },
  { year: '2019', deepLearning: 620, genomics: 460, immunotherapy: 530, radiomics: 340 },
  { year: '2020', deepLearning: 950, genomics: 510, immunotherapy: 620, radiomics: 510 },
  { year: '2021', deepLearning: 1420, genomics: 540, immunotherapy: 710, radiomics: 730 },
  { year: '2022', deepLearning: 2180, genomics: 580, immunotherapy: 780, radiomics: 1020 },
  { year: '2023', deepLearning: 3150, genomics: 610, immunotherapy: 840, radiomics: 1380 },
  { year: '2024', deepLearning: 4280, genomics: 650, immunotherapy: 910, radiomics: 1790 },
]

const fundingData = [
  { year: '2020', government: 4.2, private: 2.8 },
  { year: '2021', government: 5.1, private: 3.5 },
  { year: '2022', government: 6.3, private: 4.7 },
  { year: '2023', government: 7.8, private: 6.2 },
  { year: '2024', government: 9.5, private: 8.1 },
]

export default function ResearchTrends() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">AI 癌症研究論文發表趨勢</h3>
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={publicationsData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
            />
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
          <BarChart data={fundingData} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
            />
            <Legend />
            <Bar dataKey="government" name="政府經費" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="private" name="私人投資" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
