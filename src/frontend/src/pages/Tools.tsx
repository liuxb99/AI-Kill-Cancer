import { useNavigate } from 'react-router-dom'

const tools = [
  {
    name: '症狀分析',
    desc: '輸入症狀描述，AI 初步分析可能相關的癌症類型與建議就診科別。',
    status: '開發中',
  },
  {
    name: '風險評估',
    desc: '根據年齡、家族史、生活習慣等因子，評估個人罹癌風險等級。',
    status: '開發中',
  },
  {
    name: '治療方案比對',
    desc: '比較不同治療方式（手術、化療、放療、標靶、免疫）的適應症與副作用。',
    status: '開發中',
  },
  {
    name: '藥物查詢',
    desc: '查詢抗癌藥品資訊，包括用法、劑量、交互作用與健保給付規範。',
    status: '開發中',
  },
]

export default function Tools() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-gray-400 hover:text-primary-600 text-xl">&larr;</button>
          <h1 className="text-xl font-bold text-primary-700">AI 工具</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-12">
        <p className="text-gray-500 mb-8">智慧工具協助您了解癌症相關資訊，請選擇工具開始使用。</p>
        <div className="grid md:grid-cols-2 gap-6">
          {tools.map((t) => (
            <div
              key={t.name}
              className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition"
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold">{t.name}</h3>
                <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">
                  {t.status}
                </span>
              </div>
              <p className="text-sm text-gray-500 leading-relaxed">{t.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
