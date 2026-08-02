import { useCallback, useEffect, useState, type ReactNode } from 'react'

import {
  getRecommendation,
  type ClinicalTreatmentRecommendation,
} from '../../api/workbench'

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-4">
      <div className="h-5 w-36 rounded bg-gray-200" />
      <div className="h-4 w-full rounded bg-gray-200" />
      <div className="h-4 w-3/4 rounded bg-gray-200" />
      <div className="h-24 w-full rounded bg-gray-100" />
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="p-8 text-center">
      <p className="mb-1 text-sm font-medium text-red-500">⚠ 加载失败</p>
      <p className="text-xs text-gray-400">{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return <div className="p-8 text-center text-sm text-gray-400">{message}</div>
}

function Section({ title, icon, children }: { title: string; icon?: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-gray-100 bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-gray-50 px-4 py-3">
        {icon && <span>{icon}</span>}
        <h4 className="text-sm font-semibold text-gray-700">{title}</h4>
      </div>
      <div className="p-4">{children}</div>
    </section>
  )
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return value.map((item) => formatValue(item)).join(', ')
  return JSON.stringify(value)
}

function renderFields(value: Record<string, unknown> | null | undefined): ReactNode {
  if (!value || Object.keys(value).length === 0) return <p className="text-sm text-gray-400">暂无数据</p>
  return (
    <div className="space-y-1.5">
      {Object.entries(value).map(([key, item]) => (
        <div key={key} className="flex text-sm">
          <span className="w-32 flex-shrink-0 font-medium text-gray-500">{key}:</span>
          <span className="text-gray-800">{formatValue(item)}</span>
        </div>
      ))}
    </div>
  )
}

interface RecommendationTabProps {
  caseId: string
}

export function RecommendationTab({ caseId }: RecommendationTabProps) {
  const [data, setData] = useState<ClinicalTreatmentRecommendation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await getRecommendation(caseId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '加载治疗方案失败')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    void loadData()
  }, [loadData])

  if (loading) return <LoadingSkeleton />
  if (error) return <ErrorState message={error} />
  if (!data) return <EmptyState message="暂无治疗方案数据" />

  const hasStructuredData = Boolean(
    data.first_line || data.second_line || data.clinical_trial ||
    data.expected_benefit || data.potential_risk || data.monitoring_plan ||
    data.supporting_evidence?.length,
  )
  const hasMarkdown = Boolean(data.markdown)

  if (!hasStructuredData && !hasMarkdown) return <EmptyState message="治疗方案数据为空" />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">💊 治疗方案推荐</h3>
        <div className="flex items-center gap-3">
          {data.created_at && <span className="text-xs text-gray-400">{new Date(data.created_at).toLocaleString('zh-CN')}</span>}
          <button onClick={() => void loadData()} className="text-xs text-primary-500 hover:text-primary-700">刷新</button>
        </div>
      </div>

      {data.first_line && Object.keys(data.first_line).length > 0 && (
        <Section title="一线治疗" icon="🟢">{renderFields(data.first_line)}</Section>
      )}
      {data.second_line && Object.keys(data.second_line).length > 0 && (
        <Section title="二线治疗" icon="🟡">{renderFields(data.second_line)}</Section>
      )}
      {data.clinical_trial && Object.keys(data.clinical_trial).length > 0 && (
        <Section title="临床试验" icon="🔬">{renderFields(data.clinical_trial)}</Section>
      )}
      {data.supporting_evidence?.length > 0 && (
        <Section title="支持证据" icon="📚">
          <div className="space-y-3">
            {data.supporting_evidence.map((evidence, index) => (
              <div key={index} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                {renderFields(evidence)}
              </div>
            ))}
          </div>
        </Section>
      )}
      {data.expected_benefit && Object.keys(data.expected_benefit).length > 0 && (
        <Section title="预期效益" icon="📈">{renderFields(data.expected_benefit)}</Section>
      )}
      {data.potential_risk && Object.keys(data.potential_risk).length > 0 && (
        <Section title="潜在风险" icon="⚠️">{renderFields(data.potential_risk)}</Section>
      )}
      {data.monitoring_plan && Object.keys(data.monitoring_plan).length > 0 && (
        <Section title="监测计划" icon="📋">{renderFields(data.monitoring_plan)}</Section>
      )}
      {hasMarkdown && (
        <Section title="完整报告" icon="📄">
          <div className="whitespace-pre-wrap text-sm leading-6 text-gray-700">{data.markdown}</div>
        </Section>
      )}
      {data.context_hash && (
        <p className="border-t border-gray-100 pt-3 text-right text-xs text-gray-400">
          上下文哈希: <code className="text-gray-500">{data.context_hash.slice(0, 16)}…</code>
        </p>
      )}
    </div>
  )
}
