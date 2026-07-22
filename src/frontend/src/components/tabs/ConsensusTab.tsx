import { useEffect, useState } from 'react'
import { getConsensus, ConsensusResult } from '../../api/workbench'

interface ConsensusTabProps {
  caseId: string
}

// ─── Helper: agreement color ──────────────────────────────────────────────────

function agreementBadge(level: string): { bg: string; text: string; label: string } {
  switch (level) {
    case 'high':
      return { bg: 'bg-green-100', text: 'text-green-700', label: '高' }
    case 'moderate':
      return { bg: 'bg-amber-100', text: 'text-amber-700', label: '中' }
    case 'low':
      return { bg: 'bg-orange-100', text: 'text-orange-700', label: '低' }
    case 'none':
      return { bg: 'bg-red-100', text: 'text-red-700', label: '无' }
    default:
      return { bg: 'bg-gray-100', text: 'text-gray-600', label: level }
  }
}

function confidenceBadge(confidence: string): { bg: string; text: string } {
  const val = confidence.toLowerCase()
  if (val === 'high' || val === 'very high')
    return { bg: 'bg-green-100', text: 'text-green-700' }
  if (val === 'moderate')
    return { bg: 'bg-amber-100', text: 'text-amber-700' }
  if (val === 'low' || val === 'very low')
    return { bg: 'bg-red-100', text: 'text-red-700' }
  return { bg: 'bg-gray-100', text: 'text-gray-600' }
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-5 animate-pulse">
      <div className="h-6 w-48 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
      <div className="h-4 w-3/4 bg-gray-200 rounded" />
      <div className="h-20 w-full bg-gray-100 rounded" />
      <div className="h-4 w-1/2 bg-gray-200 rounded" />
    </div>
  )
}

// ─── ConsensusTab ────────────────────────────────────────────────────────────

export function ConsensusTab({ caseId }: ConsensusTabProps) {
  const [data, setData] = useState<ConsensusResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getConsensus(caseId)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '获取共识结果失败')
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
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-700">
        <p className="font-medium">无法加载共识结果</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    )
  }

  // ── Empty state ──
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 text-center text-gray-400">
        <p className="text-lg mb-1">🤝</p>
        <p className="text-sm">暂无共识数据</p>
      </div>
    )
  }

  // ── Data render ──
  const badge = agreementBadge(data.agreement)
  const confBadge = confidenceBadge(data.confidence)

  // Recommended option display helper
  const renderOption = (option: Record<string, any>, index?: number) => {
    if (!option || Object.keys(option).length === 0) return null
    return (
      <div className="bg-gray-50 border border-gray-100 rounded-lg p-3">
        {index !== undefined && (
          <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">
            {index === 0 ? '首选' : `备选 ${index}`}
          </p>
        )}
        {Object.entries(option).map(([key, value]) => (
          <div key={key} className="flex text-sm mb-0.5">
            <span className="text-gray-500 w-28 flex-shrink-0">{key}:</span>
            <span className="text-gray-800">{typeof value === 'string' ? value : JSON.stringify(value)}</span>
          </div>
        ))}
      </div>
    )
  }

  const hasOptions =
    data.recommended_option && Object.keys(data.recommended_option).length > 0

  const hasAlternatives =
    data.alternative_options && data.alternative_options.length > 0

  return (
    <div className="space-y-5">
      {/* Header: Agreement + Confidence */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-gray-700">🤝 共识结果</h3>
          <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${badge.bg} ${badge.text}`}>
            共识度: {badge.label}
          </span>
          <span className={`text-xs px-2.5 py-0.5 rounded-full ${confBadge.bg} ${confBadge.text}`}>
            信心度: {data.confidence}
          </span>
        </div>
        {data.created_at && (
          <span className="text-xs text-gray-400">
            {new Date(data.created_at).toLocaleString('zh-CN')}
          </span>
        )}
      </div>

      {/* Recommended Option */}
      {hasOptions && (
        <section>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            推荐方案
          </h4>
          {renderOption(data.recommended_option, 0)}
        </section>
      )}

      {/* Alternative Options */}
      {hasAlternatives && (
        <section>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            替代方案
          </h4>
          <div className="space-y-2">
            {data.alternative_options.map((opt, i) => (
              <div key={i}>{renderOption(opt, i + 1)}</div>
            ))}
          </div>
        </section>
      )}

      {/* Conflicts */}
      {data.conflicts && data.conflicts.length > 0 && (
        <section>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            ⚠️ 冲突
          </h4>
          <div className="space-y-2">
            {data.conflicts.map((conflict, i) => (
              <div key={i} className="bg-red-50 border border-red-100 rounded-lg p-3">
                {Object.entries(conflict).map(([key, value]) => (
                  <div key={key} className="flex text-sm mb-0.5">
                    <span className="text-red-600 w-28 flex-shrink-0">{key}:</span>
                    <span className="text-red-800">
                      {typeof value === 'string' ? value : JSON.stringify(value)}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Unresolved Questions */}
      {data.unresolved_questions && data.unresolved_questions.length > 0 && (
        <section>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            ❓ 未解决问题
          </h4>
          <ul className="space-y-1.5">
            {data.unresolved_questions.map((q, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-gray-300 mt-0.5">•</span>
                <span>{q}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* No data message */}
      {!hasOptions && !hasAlternatives && (!data.conflicts || data.conflicts.length === 0) && (!data.unresolved_questions || data.unresolved_questions.length === 0) && (
        <div className="text-center text-gray-400 py-6">
          <p className="text-sm">共识数据为空</p>
        </div>
      )}
    </div>
  )
}
