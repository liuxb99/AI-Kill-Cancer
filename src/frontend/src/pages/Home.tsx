import { useNavigate } from 'react-router-dom'

const features = [
  {
    title: '癌症知識庫',
    desc: '全面收錄各類癌症的成因、症狀、診斷與治療資訊，提供清晰易懂的醫學知識。',
    path: '/knowledge',
    icon: '📚',
  },
  {
    title: '用藥推薦',
    desc: '輸入基因變異（Variants），AI 智慧分析並推薦最適合的標靶藥物與治療方案。',
    path: '/recommendation',
    icon: '💊',
  },
  {
    title: 'AI 工具',
    desc: '智慧分析症狀、風險評估、治療建議，讓 AI 成為您的健康助手。',
    path: '/tools',
    icon: '🤖',
  },
  {
    title: '研究論文',
    desc: '彙整最新癌症研究論文與臨床試驗成果，掌握醫療前沿動態。',
    path: '/research',
    icon: '🔬',
  },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col min-h-screen">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-primary-700">AI Kill Cancer</h1>
          <nav className="flex gap-6 text-sm font-medium text-gray-600">
            <span className="text-primary-600 cursor-pointer">首頁</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/recommendation')}>藥物推薦</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/knowledge')}>知識庫</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/tools')}>工具</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/research')}>論文</span>
          </nav>
        </div>
      </header>

      <section className="bg-gradient-to-br from-primary-600 via-primary-500 to-accent-500 text-white">
        <div className="max-w-6xl mx-auto px-4 py-24 text-center">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            用 AI 對抗癌症
          </h2>
          <p className="text-lg md:text-xl text-white/80 max-w-2xl mx-auto mb-8">
            整合人工智慧與醫學知識，提供癌症預防、診斷輔助與治療建議的研究探索平台。<br />
            <span className="text-white/60 text-sm">⚠ 目前為原型階段，所有數據為模擬資料，不可用於臨床用途。</span>
          </p>
          <button
            onClick={() => navigate('/tools')}
            className="bg-white text-primary-600 font-semibold px-8 py-3 rounded-lg shadow-lg hover:shadow-xl transition"
          >
            開始使用 AI 工具
          </button>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 py-16">
        <div className="grid md:grid-cols-4 gap-8">
          {features.map((f) => (
            <div
              key={f.path}
              onClick={() => navigate(f.path)}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 cursor-pointer hover:shadow-md hover:-translate-y-1 transition"
            >
              <div className="text-4xl mb-4">{f.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="mt-auto bg-gray-100 border-t border-gray-200 py-6 text-center text-sm text-gray-500">
        AI Kill Cancer &copy; 2026 &mdash; 僅供學術研究與資訊參考，不構成醫療建議。
      </footer>
    </div>
  )
}
