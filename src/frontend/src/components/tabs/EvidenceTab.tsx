import { useEffect, useState } from 'react'
import { getClinicalEvidence, type EvidenceBundle } from '../../api/workbench'

// ─── Types ───────────────────────────────────────────────────────────────────

interface EvidenceTabProps {
  caseId: string
}

// ─── Badge helpers ──────────────────────────────────────────────────────────

function evidenceLevelBadge(
  level: string
): { bg: string; text: string; label: string } {
  const val = level.toLowerCase().replace(/^level\s*/i, '')
  if (val === 'a' || val === '1' || val === 'high')
    return { bg: 'bg-green-100', text: 'text-green-700', label: '高' }
  if (val === 'b' || val === '2' || val === 'moderate')
    return { bg: 'bg-blue-100', text: 'text-blue-700', label: '中' }
  if (val === 'c' || val === '3')
    return { bg: 'bg-amber-100', text: 'text-amber-700', label: '低' }
  if (val === 'd' || val === '4' || val === 'low')
    return { bg: 'bg-orange-100', text: 'text-orange-700', label: '极低' }
  return { bg: 'bg-gray-100', text: 'text-gray-600', label: level }
}

function confidenceBadge(
  confidence: string
): { bg: string; text: string; label: string } {
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
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="h-24 bg-gray-100 rounded-xl" />
        <div className="h-24 bg-gray-100 rounded-xl" />
        <div className="h-24 bg-gray-100 rounded-xl" />
        <div className="h-24 bg-gray-100 rounded-xl" />
      </div>
      {/* Source groups */}
      <div className="h-6 w-48 bg-gray-200 rounded" />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="h-12 bg-gray-100 rounded-lg" />
        <div className="h-12 bg-gray-100 rounded-lg" />
        <div className="h-12 bg-gray-100 rounded-lg" />
      </div>
      {/* Table */}
      <div className="h-6 w-36 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
      <div className="h-4 w-3/4 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-700">
      <p className="font-medium">无法加载证据数据</p>
      <p className="text-sm mt-1">{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 text-center text-gray-400">
      <p className="text-lg mb-1">📋</p>
      <p className="text-sm">{message}</p>
    </div>
  )
}

function InfoCard({
  label,
  value,
  variant = 'default',
}: {
  label: string
  value: string
  variant?: 'default' | 'primary'
}) {
  const color =
    variant === 'primary'
      ? 'text-primary-700 bg-primary-50 border-primary-100'
      : 'text-gray-700 bg-white border-gray-100'
  return (
    <div className={`rounded-lg border p-4 ${color}`}>
      <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">
        {label}
      </p>
      <p className="text-lg font-semibold">{value || '—'}</p>
    </div>
  )
}

// ─── EvidenceTab Component ──────────────────────────────────────────────────

export function EvidenceTab({ caseId }: EvidenceTabProps) {
  const [data, setData] = useState<EvidenceBundle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getClinicalEvidence(caseId)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : '获取临床证据失败')
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
  if (!data || data.total_count === 0) {
    return <EmptyState message="暂无临床证据数据" />
  }

  // ── By-source rendering ──
  const sourceEntries = data.by_source
    ? Object.entries(data.by_source)
    : []

  // ── Data render ──
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">📊 临床证据</h3>
        {data.retrieved_at && (
          <span className="text-xs text-gray-400">
            {new Date(data.retrieved_at).toLocaleString('zh-CN')}
          </span>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <InfoCard label="证据总数" value={String(data.total_count)} variant="primary" />
        <InfoCard
          label="最高证据等级"
          value={
            data.highest_level
              ? evidenceLevelBadge(data.highest_level).label
              : '—'
          }
        />
        <InfoCard
          label="来源数量"
          value={String(sourceEntries.length)}
        />
        <InfoCard
          label="冲突数"
          value={String(data.conflicts_summary?.length ?? 0)}
        />
      </div>

      {/* By-source grouping */}
      {sourceEntries.length > 0 && (
        <section>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            按来源分组
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {sourceEntries.map(([source, countOrValue]) => (
              <div
                key={source}
                className="bg-gray-50 border border-gray-100 rounded-lg px-4 py-3 flex items-center justify-between"
              >
                <span className="text-sm text-gray-700 font-medium truncate mr-2">
                  {source}
                </span>
                <span className="text-xs font-semibold text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full flex-shrink-0">
                  {typeof countOrValue === 'number'
                    ? countOrValue
                    : typeof countOrValue === 'string'
                    ? countOrValue
                    : JSON.stringify(countOrValue)}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Conflicts summary */}
      {data.conflicts_summary && data.conflicts_summary.length > 0 && (
        <section>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            ⚠️ 冲突摘要
          </h4>
          <div className="space-y-2">
            {data.conflicts_summary.map((conflict, i) => (
              <div
                key={i}
                className="bg-red-50 border border-red-100 rounded-lg p-3"
              >
                {Object.entries(conflict).map(([key, value]) => (
                  <div key={key} className="flex text-sm mb-0.5 last:mb-0">
                    <span className="text-red-600 w-28 flex-shrink-0">
                      {key}:
                    </span>
                    <span className="text-red-800">
                      {typeof value === 'string'
                        ? value
                        : JSON.stringify(value)}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Evidence list */}
      <section>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          证据列表
        </h4>
        {data.items && data.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 font-medium text-gray-600">
                    来源
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-600">
                    基因
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-600">
                    药物
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-600">
                    证据等级
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-600">
                    信心度
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item, i) => {
                  const levelStr =
                    (item.evidence_level as string) ||
                    (item.level as string) ||
                    ''
                  const confStr =
                    (item.confidence as string) ||
                    (item.confidence_level as string) ||
                    ''
                  const levelBadge = levelStr
                    ? evidenceLevelBadge(levelStr)
                    : null
                  const confBadge = confStr
                    ? confidenceBadge(confStr)
                    : null

                  return (
                    <tr
                      key={item.id || i}
                      className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-2.5 px-3 text-gray-700">
                        {(item.source as string) ||
                          (item.source_name as string) ||
                          '—'}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-gray-800">
                        {(item.gene as string) ||
                          (item.gene_symbol as string) ||
                          '—'}
                      </td>
                      <td className="py-2.5 px-3 text-gray-700">
                        {(item.drug as string) ||
                          (item.drug_name as string) ||
                          '—'}
                      </td>
                      <td className="py-2.5 px-3">
                        {levelBadge ? (
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${levelBadge.bg} ${levelBadge.text}`}
                          >
                            {levelBadge.label}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        {confBadge ? (
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full ${confBadge.bg} ${confBadge.text}`}
                          >
                            {confBadge.label}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">证据列表为空</p>
        )}
      </section>

      {/* Context hash (footer) */}
      {data.context_hash && (
        <p className="text-xs text-gray-400 text-right border-t border-gray-100 pt-3">
          上下文哈希:{' '}
          <code className="text-gray-500">
            {data.context_hash.slice(0, 16)}…
          </code>
        </p>
      )}
    </div>
  )
}
