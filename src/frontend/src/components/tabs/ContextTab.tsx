import { useEffect, useState, useCallback } from 'react'
import {
  getClinicalContext,
  type ClinicalContext,
} from '../../api/workbench'

// ─── Helper Components ──────────────────────────────────────────────────────

function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-3 p-4">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-4 bg-gray-200 rounded w-full" />
      ))}
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="p-8 text-center">
      <p className="text-red-500 text-sm font-medium mb-1">⚠ 加载失败</p>
      <p className="text-xs text-gray-400">{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="p-8 text-center">
      <p className="text-sm text-gray-400">{message}</p>
    </div>
  )
}

function InfoCard({ label, value, variant = 'default' }: { label: string; value: string; variant?: 'default' | 'primary' }) {
  const color = variant === 'primary'
    ? 'text-primary-700 bg-primary-50 border-primary-100'
    : 'text-gray-700 bg-white border-gray-100'
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

// ─── ContextTab Component ────────────────────────────────────────────────────

interface ContextTabProps {
  caseId: string
}

export function ContextTab({ caseId }: ContextTabProps) {
  const [context, setContext] = useState<ClinicalContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadContext = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getClinicalContext(caseId)
      setContext(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载临床上下文失败')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => { loadContext() }, [loadContext])

  if (loading) return <LoadingSkeleton lines={8} />
  if (error) return <ErrorState message={error} />
  if (!context) return <EmptyState message="暂无临床上下文数据" />

  return (
    <div className="space-y-6">
      {/* Demographics & Diagnosis */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <InfoCard label="年龄" value={context.age ? `${context.age} 岁` : '—'} />
        <InfoCard label="性别" value={context.gender || '—'} />
        <InfoCard label="ECOG 评分" value={context.ecog_score != null ? String(context.ecog_score) : '—'} />
        <InfoCard label="复发状态" value={context.recurrence_status || '—'} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <InfoCard label="诊断" value={context.diagnosis || '—'} variant="primary" />
        <InfoCard label="癌症类型" value={context.cancer_type || '—'} variant="primary" />
        <InfoCard label="分期" value={context.stage || '—'} variant="primary" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <InfoCard label="组织学" value={context.histology || '—'} />
        <InfoCard label="Oncotree 编码" value={context.oncotree_code || '—'} />
        <InfoCard label="患者 ID" value={context.patient_id || '—'} />
      </div>

      {/* Allergies */}
      <Section title="过敏史">
        {context.allergies && context.allergies.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {context.allergies.map((a, i) => (
              <span key={i} className="px-3 py-1 bg-red-50 text-red-700 rounded-full text-sm font-medium">
                {a}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">无已知过敏</p>
        )}
      </Section>

      {/* Biomarkers */}
      <Section title="生物标志物">
        {context.biomarkers && context.biomarkers.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {context.biomarkers.map((b, i) => (
              <span key={i} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                {b.gene || b.name || b.symbol || JSON.stringify(b)}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">暂无数据</p>
        )}
      </Section>

      {/* Variants */}
      <Section title="变异">
        {context.variants && context.variants.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 font-medium text-gray-600">基因</th>
                  <th className="text-left py-2 px-3 font-medium text-gray-600">HGVS</th>
                  <th className="text-left py-2 px-3 font-medium text-gray-600">类型</th>
                  <th className="text-left py-2 px-3 font-medium text-gray-600">意义</th>
                </tr>
              </thead>
              <tbody>
                {context.variants.map((v, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3 font-medium">{v.gene || v.gene_symbol || '—'}</td>
                    <td className="py-2 px-3 text-gray-600">{v.hgvs || v.hgvs_notation || '—'}</td>
                    <td className="py-2 px-3">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700">
                        {v.type || v.variant_type || '—'}
                      </span>
                    </td>
                    <td className="py-2 px-3">{v.significance || v.clinical_significance || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">暂无变异数据</p>
        )}
      </Section>

      {/* Treatment History */}
      <Section title="治疗史">
        {context.treatment_history && context.treatment_history.length > 0 ? (
          <ul className="space-y-2">
            {context.treatment_history.map((tx, i) => (
              <li key={i} className="text-sm bg-gray-50 rounded p-3">
                {tx.treatment || tx.regimen || tx.name ? (
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{tx.treatment || tx.regimen || tx.name}</span>
                    {tx.start_date && (
                      <span className="text-xs text-gray-400">{tx.start_date}{tx.end_date ? ` — ${tx.end_date}` : ''}</span>
                    )}
                  </div>
                ) : (
                  JSON.stringify(tx)
                )}
                {tx.response && (
                  <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full ${
                    tx.response === 'responsive' || tx.response === 'CR' || tx.response === 'PR'
                      ? 'bg-green-100 text-green-700'
                      : tx.response === 'progressive' || tx.response === 'PD'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {tx.response}
                  </span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">暂无治疗史数据</p>
        )}
      </Section>

      {/* Current Medications */}
      <Section title="当前用药">
        {context.current_medications && context.current_medications.length > 0 ? (
          <ul className="space-y-2">
            {context.current_medications.map((med, i) => (
              <li key={i} className="text-sm bg-gray-50 rounded p-3 flex items-center justify-between">
                <span className="font-medium">{med.name || med.drug || JSON.stringify(med)}</span>
                {med.dosage && <span className="text-xs text-gray-500">{med.dosage}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400">暂无用药数据</p>
        )}
      </Section>

      {/* Metastatic Sites */}
      <Section title="转移部位">
        {context.metastatic_sites && context.metastatic_sites.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {context.metastatic_sites.map((site, i) => (
              <span key={i} className="px-3 py-1 bg-orange-50 text-orange-700 rounded-full text-sm font-medium">
                {site}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">无远处转移</p>
        )}
      </Section>

      {/* Clinical Notes */}
      {context.clinical_notes && (
        <Section title="临床备注">
          <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap">
            {context.clinical_notes}
          </div>
        </Section>
      )}

      {/* Context Hash (footer metadata) */}
      {context.context_hash && (
        <p className="text-xs text-gray-400 text-right border-t border-gray-100 pt-3 mt-6">
          上下文哈希: <code className="text-gray-500">{context.context_hash.slice(0, 16)}…</code>
        </p>
      )}
    </div>
  )
}
