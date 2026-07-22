import { useEffect, useState } from 'react'
import { runAgents, type AgentOpinion } from '../../api/workbench'

// ─── Confidence badge helpers ─────────────────────────────────────────────────

function confidenceBadge(confidence: string): { bg: string; text: string; label: string } {
  const val = confidence.toLowerCase()
  if (val === 'very high')
    return { bg: 'bg-green-100', text: 'text-green-700', label: '非常高' }
  if (val === 'high')
    return { bg: 'bg-green-50', text: 'text-green-600', label: '高' }
  if (val === 'moderate')
    return { bg: 'bg-amber-100', text: 'text-amber-700', label: '中' }
  if (val === 'low')
    return { bg: 'bg-orange-100', text: 'text-orange-700', label: '低' }
  if (val === 'very low')
    return { bg: 'bg-red-100', text: 'text-red-700', label: '非常低' }
  return { bg: 'bg-gray-100', text: 'text-gray-600', label: confidence }
}

// ─── Helper Components ──────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-5 animate-pulse">
      <div className="h-6 w-48 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
      <div className="h-4 w-3/4 bg-gray-200 rounded" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="h-40 bg-gray-100 rounded-xl" />
        <div className="h-40 bg-gray-100 rounded-xl" />
      </div>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-700">
      <p className="font-medium">无法加载智能体意见</p>
      <p className="text-sm mt-1">{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 text-center text-gray-400">
      <p className="text-lg mb-1">🤖</p>
      <p className="text-sm">{message}</p>
    </div>
  )
}

// ─── Agent Card ─────────────────────────────────────────────────────────────

function AgentCard({ opinion }: { opinion: AgentOpinion }) {
  const badge = confidenceBadge(opinion.confidence)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4 transition-shadow hover:shadow-md">
      {/* Header: Agent name + version + confidence */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white text-sm font-bold">
            {opinion.agent_type.charAt(0).toUpperCase()}
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-800">{opinion.agent_type}</h4>
            <span className="text-xs text-gray-400">v{opinion.agent_version}</span>
          </div>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${badge.bg} ${badge.text}`}>
          信心度: {badge.label}
        </span>
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-700 leading-relaxed">{opinion.summary}</p>

      {/* Pros / Cons grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Pros */}
        <div>
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <span className="text-green-500">✓</span> 支持论点
          </h5>
          {opinion.pros && opinion.pros.length > 0 ? (
            <ul className="space-y-1">
              {opinion.pros.map((pro, i) => (
                <li key={i} className="flex items-start gap-1.5 text-sm text-gray-700">
                  <span className="text-green-400 mt-0.5 flex-shrink-0">•</span>
                  <span>{pro}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-gray-400">无支持论点</p>
          )}
        </div>

        {/* Cons */}
        <div>
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <span className="text-red-500">✗</span> 反对论点
          </h5>
          {opinion.cons && opinion.cons.length > 0 ? (
            <ul className="space-y-1">
              {opinion.cons.map((con, i) => (
                <li key={i} className="flex items-start gap-1.5 text-sm text-gray-700">
                  <span className="text-red-400 mt-0.5 flex-shrink-0">•</span>
                  <span>{con}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-gray-400">无反对论点</p>
          )}
        </div>
      </div>

      {/* References */}
      {opinion.references && opinion.references.length > 0 && (
        <div className="border-t border-gray-100 pt-3">
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            参考文献
          </h5>
          <ul className="space-y-1">
            {opinion.references.map((ref, i) => (
              <li key={i} className="text-xs text-gray-500 flex items-start gap-1.5">
                <span className="text-gray-300 mt-0.5 flex-shrink-0">[{i + 1}]</span>
                <span>
                  {ref.title || ref.citation || ref.url || JSON.stringify(ref)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Created at */}
      {opinion.created_at && (
        <p className="text-xs text-gray-400 text-right border-t border-gray-50 pt-2">
          {new Date(opinion.created_at).toLocaleString('zh-CN')}
        </p>
      )}
    </div>
  )
}

// ─── AgentsTab Component ─────────────────────────────────────────────────────

interface AgentsTabProps {
  caseId: string
}

export function AgentsTab({ caseId }: AgentsTabProps) {
  const [opinions, setOpinions] = useState<AgentOpinion[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    runAgents(caseId)
      .then((res) => {
        if (!cancelled) setOpinions(res)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '获取智能体意见失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [caseId])

  // ── Loading state ──
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <LoadingSkeleton />
      </div>
    )
  }

  // ── Error state ──
  if (error) {
    return <ErrorState message={error} />
  }

  // ── Empty state ──
  if (!opinions || opinions.length === 0) {
    return <EmptyState message="暂无智能体意见数据" />
  }

  // ── Data render ──
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">🧠 智能体意见</h3>
        <span className="text-xs text-gray-400">
          共 {opinions.length} 个智能体
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {opinions.map((opinion, index) => (
          <AgentCard key={`${opinion.agent_type}-${index}`} opinion={opinion} />
        ))}
      </div>
    </div>
  )
}
