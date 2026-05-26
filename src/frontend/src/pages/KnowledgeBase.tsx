import { useNavigate } from 'react-router-dom'

const categories = [
  { name: '肺癌', desc: '致病因素、篩檢方式、標靶治療與免疫治療進展', color: 'bg-rose-50 border-rose-200' },
  { name: '肝癌', desc: 'B/C 型肝炎防治、早期診斷與局部治療選擇', color: 'bg-amber-50 border-amber-200' },
  { name: '大腸癌', desc: '息肉演變路徑、糞便潛血篩檢與精準醫療', color: 'bg-emerald-50 border-emerald-200' },
  { name: '乳癌', desc: '遺傳風險評估、荷爾蒙治療與 HER2 標靶藥物', color: 'bg-pink-50 border-pink-200' },
  { name: '攝護腺癌', desc: 'PSA 篩檢爭議、主動監控與根治性治療', color: 'bg-sky-50 border-sky-200' },
  { name: '胃癌', desc: '幽門桿菌根除、內視鏡切除與化療策略', color: 'bg-violet-50 border-violet-200' },
]

export default function KnowledgeBase() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-gray-400 hover:text-primary-600 text-xl">&larr;</button>
          <h1 className="text-xl font-bold text-primary-700">癌症知識庫</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-12">
        <p className="text-gray-500 mb-8">依癌症類型分類，點選查看詳細醫學知識。</p>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((c) => (
            <div
              key={c.name}
              className={`rounded-xl border p-6 cursor-pointer hover:shadow-md transition ${c.color}`}
            >
              <h3 className="text-lg font-semibold mb-2">{c.name}</h3>
              <p className="text-sm text-gray-600 leading-relaxed">{c.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
