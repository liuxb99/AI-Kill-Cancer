import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

type DemoCase = {
  case_key: string
  display_name?: string
  cancer_type?: string
  stage?: string
  radioiodine_status?: string
  variant: { gene?: string; hgvs_p?: string; variant_type?: string; driver_status?: string }
  drug: { name?: string; mechanism?: string }
  evidence: { level?: string; direction?: string; summary?: string; synthetic: boolean }
  publication: { title?: string; journal?: string }
  clinical_trial: { id?: string; title?: string; status?: string }
}

const features = [
  { title: '癌症知識庫', desc: '全面收錄各類癌症的成因、症狀、診斷與治療資訊。', path: '/knowledge', icon: '📚' },
  { title: '用藥推薦', desc: '依基因變異、證據與研究資料展示 Precision Oncology 推理流程。', path: '/recommendation', icon: '💊' },
  { title: 'AI 工具', desc: '研究分析、風險評估與輔助推理工具。', path: '/tools', icon: '🤖' },
  { title: '研究論文', desc: '展示論文、證據與臨床試驗之間的可追溯關聯。', path: '/research', icon: '🔬' },
]

export default function Home() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<DemoCase[]>([])
  const [selected, setSelected] = useState(0)

  useEffect(() => {
    fetch('/api/v1/demo/cases')
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error('demo API failed'))))
      .then((data) => setCases(Array.isArray(data.items) ? data.items : []))
      .catch(() => setCases([]))
  }, [])

  const demo = cases[selected]

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
        <div className="max-w-6xl mx-auto px-4 py-20 text-center">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">用 AI 對抗癌症</h2>
          <p className="text-lg md:text-xl text-white/80 max-w-3xl mx-auto mb-8">
            Local-First Precision Oncology 研究平台；線上版使用合成 CSV 病例展示完整證據鏈，本地版以持久化 SQLite 作主要工作資料庫。<br />
            <span className="text-white/60 text-sm">⚠ 線上病例、論文、證據、藥物與試驗資料皆為 synthetic demo，不可用於診斷或治療。</span>
          </p>
          <button onClick={() => navigate('/tools')} className="bg-white text-primary-600 font-semibold px-8 py-3 rounded-lg shadow-lg hover:shadow-xl transition">
            開始探索研究功能
          </button>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 pt-14">
        <div className="flex items-end justify-between gap-4 mb-5">
          <div>
            <p className="text-xs font-semibold tracking-widest text-amber-600 uppercase">Demo Showcase</p>
            <h3 className="text-2xl font-bold">示範 Precision Oncology 病例</h3>
            <p className="text-sm text-gray-500 mt-1">切換病例查看 Variant → Evidence → Drug → Publication → Trial 的展示鏈。</p>
          </div>
          {cases.length > 0 && <span className="text-sm text-gray-400">{cases.length} 個 synthetic cases</span>}
        </div>

        {cases.length > 0 ? (
          <>
            <div className="flex flex-wrap gap-2 mb-6">
              {cases.map((item, index) => (
                <button key={item.case_key} onClick={() => setSelected(index)} className={`px-4 py-2 rounded-full text-sm border transition ${selected === index ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-600 border-gray-200 hover:border-primary-300'}`}>
                  {item.display_name || item.case_key} · {item.variant.gene || 'Variant'}
                </button>
              ))}
            </div>
            {demo && (
              <div className="grid lg:grid-cols-3 gap-5 bg-white border border-gray-100 shadow-sm rounded-2xl p-6">
                <div>
                  <div className="text-xs text-gray-400 mb-1">病例 / 分子特徵</div>
                  <div className="font-semibold text-lg">{demo.display_name} · {demo.cancer_type}</div>
                  <div className="text-sm text-gray-500 mt-2">Stage {demo.stage || '—'} · RAI {demo.radioiodine_status || '—'}</div>
                  <div className="mt-4 rounded-lg bg-gray-50 p-4">
                    <div className="font-semibold">{demo.variant.gene} {demo.variant.hgvs_p}</div>
                    <div className="text-xs text-gray-500 mt-1">{demo.variant.variant_type} · {demo.variant.driver_status}</div>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-400 mb-1">展示藥物 / 證據</div>
                  <div className="font-semibold text-lg">{demo.drug.name || '—'}</div>
                  <p className="text-sm text-gray-500 mt-2">{demo.drug.mechanism}</p>
                  <div className="mt-4 text-sm"><span className="font-medium">Evidence：</span>{demo.evidence.level} · {demo.evidence.direction}</div>
                  <p className="text-xs text-amber-600 mt-2">Synthetic evidence — 僅供功能展示</p>
                </div>
                <div>
                  <div className="text-xs text-gray-400 mb-1">來源鏈展示</div>
                  <div className="text-sm font-medium">{demo.publication.title || '—'}</div>
                  <div className="text-xs text-gray-500 mt-1">{demo.publication.journal}</div>
                  <div className="mt-4 text-sm font-medium">{demo.clinical_trial.id} · {demo.clinical_trial.status}</div>
                  <div className="text-xs text-gray-500 mt-1">{demo.clinical_trial.title}</div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">示範資料載入中；若線上 Demo API 暫不可用，其他功能仍可繼續使用。</div>
        )}
      </section>

      <section className="max-w-6xl mx-auto px-4 py-14">
        <div className="grid md:grid-cols-4 gap-8">
          {features.map((f) => (
            <div key={f.path} onClick={() => navigate(f.path)} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 cursor-pointer hover:shadow-md hover:-translate-y-1 transition">
              <div className="text-4xl mb-4">{f.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="mt-auto bg-gray-100 border-t border-gray-200 py-6 text-center text-sm text-gray-500">
        AI Kill Cancer &copy; 2026 &mdash; 研究與展示用途，不構成醫療建議。
      </footer>
    </div>
  )
}
