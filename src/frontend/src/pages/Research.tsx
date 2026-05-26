import { useNavigate } from 'react-router-dom'

const papers = [
  {
    title: 'Deep learning for early cancer detection: a systematic review',
    journal: 'Nature Medicine',
    year: 2025,
    authors: 'Chen X. et al.',
    tags: ['深度學習', '早期篩檢'],
  },
  {
    title: 'Immunotherapy combinations in advanced NSCLC: phase III results',
    journal: 'The Lancet Oncology',
    year: 2025,
    authors: 'Wang L., Kim S. et al.',
    tags: ['免疫治療', '肺癌'],
  },
  {
    title: 'Liquid biopsy multi-cancer early detection in asymptomatic populations',
    journal: 'New England Journal of Medicine',
    year: 2024,
    authors: 'Zhang Y. et al.',
    tags: ['液態切片', '早期診斷'],
  },
  {
    title: 'AI-powered pathology grading for breast cancer prognosis',
    journal: 'JAMA Oncology',
    year: 2024,
    authors: 'Liu R., Patel A. et al.',
    tags: ['病理 AI', '乳癌'],
  },
]

export default function Research() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-gray-400 hover:text-primary-600 text-xl">&larr;</button>
          <h1 className="text-xl font-bold text-primary-700">研究論文</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-12">
        <p className="text-gray-500 mb-8">癌症與 AI 領域最新研究論文整理。</p>
        <div className="space-y-4">
          {papers.map((p, i) => (
            <div
              key={i}
              className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition"
            >
              <h3 className="text-base font-semibold mb-1">{p.title}</h3>
              <p className="text-sm text-gray-500 mb-2">
                {p.journal} &middot; {p.year} &middot; {p.authors}
              </p>
              <div className="flex gap-2">
                {p.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs bg-primary-50 text-primary-600 px-2 py-0.5 rounded-full"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
