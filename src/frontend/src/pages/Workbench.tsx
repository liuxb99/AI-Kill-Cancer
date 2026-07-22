import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  getPatientSummary,
  getTimeline,
  getKnowledgeGraph,
  getTreatmentRecommendation,
  getActivityLog,
  addTumorBoardVote,
  type PatientSummary,
  type WorkbenchTimeline,
  type KnowledgeGraph,
  type TreatmentRecommendation,
  type ActivityLog,
} from '../api/workbench'

// ─── Tab config ─────────────────────────────────────────────────────────────

interface TabItem {
  id: string
  label: string
  icon: string
}

const TABS: TabItem[] = [
  { id: 'patient', label: '患者', icon: '👤' },
  { id: 'clinical-notes', label: '临床笔记', icon: '📝' },
  { id: 'pathology', label: '病理', icon: '🔬' },
  { id: 'variants', label: '变异', icon: '🧬' },
  { id: 'knowledge', label: '知识图谱', icon: '🔗' },
  { id: 'reasoning', label: 'AI 推理', icon: '🤖' },
  { id: 'treatment', label: '治疗方案', icon: '💊' },
  { id: 'tumor-board', label: '肿瘤委员会', icon: '👥' },
]

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-3 p-4">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-4 bg-gray-200 rounded w-full" />
      ))}
    </div>
  )
}

// ─── Sub-panels ──────────────────────────────────────────────────────────────

function PatientPanel({ summary }: { summary: PatientSummary | null }) {
  if (!summary) return <LoadingSkeleton lines={8} />
  const { patient, diagnosis, stage, cancer_type, biomarkers, treatment_history, current_medications, case_status } = summary
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <InfoCard label="姓名/ID" value={patient.mrn || patient.id.slice(0, 8) || '—'} />
        <InfoCard label="年龄/性别" value={`${patient.age || '—'}岁 / ${patient.sex || '—'}`} />
        <InfoCard label="种族" value={patient.race || '—'} />
        <InfoCard label="民族" value={patient.ethnicity || '—'} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <InfoCard label="癌症类型" value={cancer_type || '—'} variant="primary" />
        <InfoCard label="分期" value={stage || '—'} variant="primary" />
        <InfoCard label="诊断" value={diagnosis || '—'} />
        <InfoCard label="案例状态" value={case_status || '—'} />
      </div>
      <Section title="生物标志物">
        {biomarkers.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {biomarkers.map((b, i) => (
              <span key={i} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">{b}</span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">暂无数据</p>
        )}
      </Section>
      <Section title="治疗史">
        {treatment_history.length > 0 ? (
          <ul className="space-y-2">
            {treatment_history.map((tx, i) => (
              <li key={i} className="text-sm bg-gray-50 rounded p-2">{JSON.stringify(tx)}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">暂无数据</p>
        )}
      </Section>
      <Section title="当前用药">
        {current_medications.length > 0 ? (
          <ul className="space-y-2">
            {current_medications.map((med, i) => (
              <li key={i} className="text-sm bg-gray-50 rounded p-2">{JSON.stringify(med)}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">暂无数据</p>
        )}
      </Section>
    </div>
  )
}

function InfoCard({ label, value, variant = 'default' }: { label: string; value: string; variant?: 'default' | 'primary' }) {
  const color = variant === 'primary' ? 'text-primary-700 bg-primary-50 border-primary-100' : 'text-gray-700 bg-white border-gray-100'
  return (
    <div className={`rounded-lg border p-4 ${color}`}>
      <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold">{value || '—'}</p>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{title}</h3>
      {children}
    </div>
  )
}

function ClinicalNotesPanel() {
  const [note, setNote] = useState('')
  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">自由文本临床笔记</p>
      <textarea
        className="w-full h-48 border border-gray-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        placeholder="输入临床笔记..."
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
    </div>
  )
}

function PathologyPanel() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">病理学数据将在此显示。可在"上传"模块上传病理报告。</p>
      <div className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center text-gray-400">
        <p className="text-lg mb-2">📄</p>
        <p className="text-sm">尚未上传病理报告</p>
      </div>
    </div>
  )
}

function VariantsPanel({ graph }: { graph: KnowledgeGraph | null }) {
  if (!graph) return <LoadingSkeleton lines={5} />
  const variants = graph.nodes.filter(n => n.node_type === 'variant')
  const genes = graph.nodes.filter(n => n.node_type === 'gene')
  if (variants.length === 0 && genes.length === 0) {
    return <p className="text-sm text-gray-400 p-4">未检测到变异</p>
  }
  return (
    <div className="space-y-4">
      <Section title="基因">
        <div className="flex flex-wrap gap-2">
          {genes.map(g => (
            <span key={g.id} className="px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm font-medium">{g.label}</span>
          ))}
        </div>
      </Section>
      <Section title="变异列表">
        <div className="space-y-2">
          {variants.map(v => (
            <div key={v.id} className="flex items-center gap-3 bg-white border border-gray-100 rounded-lg p-3">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: v.color }} />
              <span className="text-sm font-medium text-gray-700">{v.label}</span>
              <span className="text-xs text-gray-400 ml-auto">{v.id}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}

function KnowledgePanel({ graph }: { graph: KnowledgeGraph | null }) {
  if (!graph) return <LoadingSkeleton lines={5} />
  const { nodes, edges } = graph
  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-100 rounded-lg p-4">
        <p className="text-sm font-medium text-gray-700 mb-3">知识图谱 ({nodes.length} 节点, {edges.length} 边)</p>
        <div className="flex flex-wrap gap-2">
          {nodes.map(n => (
            <div key={n.id} className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
              style={{ backgroundColor: n.color + '20', color: n.color }}>
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: n.color }} />
              {n.label}
              <span className="text-gray-400 ml-1">({n.node_type})</span>
            </div>
          ))}
        </div>
      </div>
      <Section title="关系">
        <div className="space-y-1">
          {edges.map((e, i) => (
            <div key={i} className="text-xs text-gray-500 flex items-center gap-2 p-1">
              <span className="font-medium text-gray-700">{e.source_id}</span>
              <span className="text-primary-500">─{e.label}→</span>
              <span className="font-medium text-gray-700">{e.target_id}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}

function ReasoningPanel({ caseId }: { caseId: string }) {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([])
  const [input, setInput] = useState('')
  const sendMessage = useCallback(() => {
    if (!input.trim()) return
    setMessages(prev => [...prev, { role: 'user', content: input }])
    setMessages(prev => [...prev, { role: 'ai', content: `[模拟] 基于案例 ${caseId.slice(0, 8)} 的分析结果：建议进行证据验证。` }])
    setInput('')
  }, [input, caseId])
  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex-1 space-y-3 overflow-y-auto max-h-80">
        {messages.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-8">开始与 AI 助手对话以进行临床推理</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-3 text-sm ${
              m.role === 'user' ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-700'
            }`}>
              {m.content}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          placeholder="向 AI 推理引擎提问..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button onClick={sendMessage} className="px-4 py-2 bg-primary-500 text-white rounded-lg text-sm hover:bg-primary-600 transition">
          发送
        </button>
      </div>
    </div>
  )
}

function TreatmentPanel({ treatment }: { treatment: TreatmentRecommendation | null }) {
  if (!treatment) return <LoadingSkeleton lines={5} />
  const { recommendations, alternatives, contraindicatio, evidence_summary } = treatment as TreatmentRecommendation & { contraindicatio?: DrugInfo[] }
  const contraindications = contraindicatio || treatment.contraindications || []
  return (
    <div className="space-y-6">
      <Section title="推荐方案">
        {recommendations.length > 0 ? (
          <div className="space-y-3">
            {recommendations.map((d, i) => (
              <div key={i} className="bg-green-50 border border-green-100 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-green-800">{d.name}</h4>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    d.status === 'approved' ? 'bg-green-200 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>{d.status}</span>
                </div>
                <p className="text-sm text-gray-600 mt-1">{d.mechanism || '机制未知'}</p>
                <div className="flex gap-4 mt-2 text-xs text-gray-500">
                  <span>匹配: {d.match_level}</span>
                  <span>证据等级: {d.level}</span>
                  <span>置信度: {(d.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">暂无推荐方案</p>
        )}
      </Section>
      <Section title="替代方案">
        {alternatives.length > 0 ? (
          <div className="space-y-2">
            {alternatives.map((d, i) => (
              <div key={i} className="bg-gray-50 border border-gray-100 rounded-lg p-3">
                <h4 className="font-medium text-gray-700">{d.name}</h4>
                <p className="text-xs text-gray-500 mt-1">{d.mechanism}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">暂无替代方案</p>
        )}
      </Section>
      <Section title="禁忌症">
        {contraindications.length > 0 ? (
          <div className="space-y-2">
            {contraindications.map((d, i) => (
              <div key={i} className="bg-red-50 border border-red-100 rounded-lg p-3">
                <h4 className="font-medium text-red-700">{d.name}</h4>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">未发现禁忌症</p>
        )}
      </Section>
      {evidence_summary && (
        <Section title="证据摘要">
          <p className="text-sm text-gray-600 bg-blue-50 rounded-lg p-3">{evidence_summary}</p>
        </Section>
      )}
    </div>
  )
}

function TumorBoardPanel({ caseId }: { caseId: string }) {
  const [votes, setVotes] = useState<Array<{ reviewer: string; vote: string; rationale: string }>>([])
  const [showForm, setShowForm] = useState(false)
  const [voteVal, setVoteVal] = useState('approve')
  const [rationale, setRationale] = useState('')
  const submitVote = useCallback(async () => {
    try {
      await addTumorBoardVote(caseId, { vote: voteVal, rationale, reviewer_name: 'Current User' })
      setVotes(prev => [...prev, { reviewer: 'Current User', vote: voteVal, rationale }])
      setShowForm(false)
      setRationale('')
    } catch (e) {
      console.error('Vote failed:', e)
    }
  }, [caseId, voteVal, rationale])
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">肿瘤委员会讨论</h3>
        <button onClick={() => setShowForm(!showForm)}
          className="text-xs px-3 py-1.5 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition">
          {showForm ? '取消' : '添加投票'}
        </button>
      </div>
      {showForm && (
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <div className="flex gap-4">
            {['approve', 'reject', 'abstain'].map(v => (
              <label key={v} className="flex items-center gap-2 text-sm">
                <input type="radio" name="vote" value={v} checked={voteVal === v}
                  onChange={() => setVoteVal(v)} />
                {v === 'approve' ? '批准' : v === 'reject' ? '拒绝' : '弃权'}
              </label>
            ))}
          </div>
          <textarea className="w-full border border-gray-200 rounded-lg p-2 text-sm"
            placeholder="投票理由..." value={rationale} onChange={(e) => setRationale(e.target.value)} />
          <button onClick={submitVote} className="px-4 py-2 bg-primary-500 text-white rounded-lg text-sm hover:bg-primary-600 transition">
            提交投票
          </button>
        </div>
      )}
      <div className="space-y-3">
        {votes.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">尚无投票</p>
        ) : (
          votes.map((v, i) => (
            <div key={i} className="bg-white border border-gray-100 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{v.reviewer}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  v.vote === 'approve' ? 'bg-green-100 text-green-700' :
                  v.vote === 'reject' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
                }`}>{v.vote}</span>
              </div>
              {v.rationale && <p className="text-sm text-gray-500 mt-1">{v.rationale}</p>}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ─── Main Workbench Component ────────────────────────────────────────────────

export default function Workbench() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const caseId = searchParams.get('caseId') || ''

  const [activeTab, setActiveTab] = useState('patient')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [patientSummary, setPatientSummary] = useState<PatientSummary | null>(null)
  const [timeline, setTimeline] = useState<WorkbenchTimeline | null>(null)
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null)
  const [treatment, setTreatment] = useState<TreatmentRecommendation | null>(null)
  const [activityLog, setActivityLog] = useState<ActivityLog | null>(null)

  useEffect(() => {
    if (!caseId) {
      setLoading(false)
      setError('请在 URL 中指定案例 ID (?caseId=...)')
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([
      getPatientSummary(caseId).catch(() => null),
      getTimeline(caseId).catch(() => null),
      getKnowledgeGraph(caseId).catch(() => null),
      getTreatmentRecommendation(caseId).catch(() => null),
      getActivityLog(caseId, 10).catch(() => null),
    ]).then(([ps, tl, kg, tr, al]) => {
      if (cancelled) return
      setPatientSummary(ps)
      setTimeline(tl)
      setGraph(kg)
      setTreatment(tr)
      setActivityLog(al)
    }).catch((e) => {
      if (!cancelled) setError(e.message || '加载工作台失败')
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })

    return () => { cancelled = true }
  }, [caseId])

  if (error) {
    return (
      <div className="flex flex-col min-h-screen">
        <header className="bg-white shadow-sm border-b border-gray-200 px-4 py-3">
          <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-primary-600 transition">&larr; 返回首页</button>
        </header>
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-500 font-medium mb-2">⚠ 加载失败</p>
            <p className="text-sm text-gray-500">{error}</p>
          </div>
        </main>
      </div>
    )
  }

  if (!caseId) {
    return (
      <div className="flex flex-col min-h-screen">
        <header className="bg-white shadow-sm border-b border-gray-200 px-4 py-3">
          <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-primary-600 transition">&larr; 返回首页</button>
        </header>
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-lg font-medium text-gray-700 mb-2">临床工作台</p>
            <p className="text-sm text-gray-400">请从案例列表选择一个案例</p>
          </div>
        </main>
      </div>
    )
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'patient': return <PatientPanel summary={patientSummary} />
      case 'clinical-notes': return <ClinicalNotesPanel />
      case 'pathology': return <PathologyPanel />
      case 'variants': return <VariantsPanel graph={graph} />
      case 'knowledge': return <KnowledgePanel graph={graph} />
      case 'reasoning': return <ReasoningPanel caseId={caseId} />
      case 'treatment': return <TreatmentPanel treatment={treatment} />
      case 'tumor-board': return <TumorBoardPanel caseId={caseId} />
      default: return <PatientPanel summary={patientSummary} />
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      {/* ── Top Bar: Patient Summary ── */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')}
              className="text-sm text-gray-500 hover:text-primary-600 transition">&larr; 返回</button>
            <h1 className="text-lg font-bold text-primary-700">临床工作台</h1>
            {patientSummary && (
              <span className="text-xs bg-primary-50 text-primary-600 px-2 py-0.5 rounded-full font-medium">
                {patientSummary.cancer_type || '案例'} · {patientSummary.stage || 'N/A'}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            {loading && <span className="animate-pulse">加载中...</span>}
            {!loading && <span>案例: {caseId.slice(0, 8)}...</span>}
          </div>
        </div>
        {/* Alerts bar */}
        {patientSummary && patientSummary.alerts && patientSummary.alerts.length > 0 && (
          <div className="bg-red-50 border-t border-red-100 px-4 py-1.5 text-xs text-red-700 flex gap-2">
            <span className="font-medium">⚠ 提醒:</span>
            {patientSummary.alerts.map((a, i) => (
              <span key={i}>{JSON.stringify(a)}</span>
            ))}
          </div>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ── Left Sidebar ── */}
        <nav className="w-56 bg-white border-r border-gray-200 flex-shrink-0 overflow-y-auto">
          <div className="p-3 space-y-1">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide px-2 mb-2">导航</p>
            {[
              { id: 'patient', label: '患者', icon: '👤' },
              { id: 'case', label: '案例', icon: '📁' },
              { id: 'specimen', label: '标本', icon: '🧪' },
              { id: 'sequencing', label: '测序', icon: '🧬' },
              { id: 'variants', label: '变异', icon: '🔬' },
              { id: 'reports', label: '报告', icon: '📊' },
              { id: 'knowledge', label: '知识', icon: '🔗' },
              { id: 'history', label: '历史', icon: '📋' },
            ].map(item => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id === 'case' ? 'patient' : item.id === 'specimen' ? 'pathology' : item.id === 'sequencing' ? 'variants' : item.id === 'reports' ? 'treatment' : item.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                  activeTab === item.id ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <span>{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        </nav>

        {/* ── Center: Tab Content ── */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Tab bar */}
          <div className="bg-white border-b border-gray-200 flex overflow-x-auto">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-700'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-1.5">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? <LoadingSkeleton lines={10} /> : renderTabContent()}
          </div>
        </main>

        {/* ── Right Sidebar: AI Assistant ── */}
        <aside className="w-72 bg-white border-l border-gray-200 flex-shrink-0 flex flex-col">
          <div className="p-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700">AI 助手</h3>
          </div>
          <div className="flex-1 p-3 overflow-y-auto space-y-3">
            {treatment && treatment.recommendations && treatment.recommendations.length > 0 && (
              <div className="bg-green-50 border border-green-100 rounded-lg p-3">
                <p className="text-xs font-medium text-green-700 mb-1">💊 推荐方案</p>
                {treatment.recommendations.slice(0, 3).map((d, i) => (
                  <p key={i} className="text-xs text-green-600">{d.name} ({(d.confidence * 100).toFixed(0)}%)</p>
                ))}
              </div>
            )}
            {timeline && timeline.events && timeline.events.length > 0 && (
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
                <p className="text-xs font-medium text-blue-700 mb-1">📋 最新活动</p>
                <p className="text-xs text-blue-600">{timeline.events[0]?.description}</p>
              </div>
            )}
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs font-medium text-gray-700 mb-1">🔍 证据参考</p>
              <p className="text-xs text-gray-500">点击知识图谱查看详细证据来源</p>
            </div>
          </div>
          <div className="p-3 border-t border-gray-100">
            <p className="text-xs text-gray-400 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
              系统就绪 — {patientSummary?.case_status || 'active'}
            </p>
          </div>
        </aside>
      </div>

      {/* ── Bottom: Activity Log ── */}
      <footer className="bg-white border-t border-gray-200">
        <div className="px-4 py-2 flex items-center justify-between">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">活动日志</h4>
          {activityLog && <span className="text-xs text-gray-400">{activityLog.total} 条记录</span>}
        </div>
        <div className="px-4 pb-2 flex gap-4 overflow-x-auto text-xs text-gray-500 max-w-full">
          {activityLog && activityLog.entries.length > 0 ? (
            activityLog.entries.slice(0, 5).map((entry, i) => (
              <div key={i} className="flex items-center gap-2 whitespace-nowrap bg-gray-50 rounded px-2 py-1">
                <span className={`w-1.5 h-1.5 rounded-full ${entry.action === 'system' ? 'bg-gray-300' : 'bg-primary-400'}`} />
                <span>{entry.action}</span>
                <span className="text-gray-300">|</span>
                <span>{new Date(entry.created_at).toLocaleString('zh-CN')}</span>
              </div>
            ))
          ) : (
            <span className="text-gray-300">暂无活动</span>
          )}
        </div>
      </footer>
    </div>
  )
}

// Re-export DrugInfo type for TreatmentPanel
interface DrugInfo {
  name: string
  drugbank_id: string
  mechanism: string
  status: string
  level: string
  match_level: string
  confidence: number
}
