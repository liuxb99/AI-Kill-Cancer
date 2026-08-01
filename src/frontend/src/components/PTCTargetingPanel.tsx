import { useEffect, useState } from 'react'

import { getPTCTargeting, type PTCTargetingResponse } from '../api/ptcTargeting'

interface Props {
  gene: string | null
  proteinChange?: string | null
  onFocusResidue?: (residue: number) => void
}

function residueNumber(proteinChange?: string | null): number | null {
  if (!proteinChange) return null
  const match = proteinChange.match(/(?:p\.)?[A-Za-z*]+(\d+)/)
  return match ? Number(match[1]) : null
}

export default function PTCTargetingPanel({ gene, proteinChange, onFocusResidue }: Props) {
  const [data, setData] = useState<PTCTargetingResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!gene) {
      setData(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    void getPTCTargeting(gene)
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : '无法载入靶向治疗链')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [gene])

  if (!gene) {
    return (
      <section className="rounded-xl border bg-white p-5 shadow-sm">
        <h3 className="font-bold text-gray-900">突变 → 靶点 → 药物 → 证据</h3>
        <p className="mt-2 text-sm text-gray-500">选择病例中的基因后显示完整研究链。</p>
      </section>
    )
  }

  if (loading) return <section className="rounded-xl border bg-white p-5 shadow-sm">载入 {gene} 靶向治疗链…</section>
  if (error) return <section className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700">{error}</section>
  if (!data) return null

  const residue = residueNumber(proteinChange)
  const domain = data.pathway.domain_range
  const insideDomain = residue && domain ? residue >= domain[0] && residue <= domain[1] : null

  return (
    <section className="rounded-xl border bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-600">Mutation Targeting Chain</p>
          <h3 className="text-xl font-bold text-gray-900">{data.gene} · {data.pathway.pathway}</h3>
          <p className="text-sm text-gray-500">{data.pathway.protein_domain}{domain ? ` · residues ${domain[0]}–${domain[1]}` : ''}</p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="rounded bg-cyan-50 px-2 py-1 text-cyan-700">{data.counts.therapies} therapies</span>
          <span className="rounded bg-amber-50 px-2 py-1 text-amber-700">{data.counts.evidence} evidence</span>
          <span className="rounded bg-emerald-50 px-2 py-1 text-emerald-700">{data.counts.trials} trials</span>
        </div>
      </div>

      {proteinChange && residue && (
        <div className={`mt-4 rounded border p-3 text-sm ${insideDomain ? 'border-orange-300 bg-orange-50 text-orange-900' : 'border-gray-200 bg-gray-50 text-gray-700'}`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span><strong>{proteinChange}</strong> · residue {residue}{insideDomain === true ? ' · 位于目标结构域' : insideDomain === false ? ' · 位于目标结构域之外' : ''}</span>
            {onFocusResidue && <button className="rounded bg-orange-500 px-3 py-1.5 font-semibold text-white" onClick={() => onFocusResidue(residue)}>在 3D 中聚焦</button>}
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
        <span className="font-semibold text-gray-700">讯号路径：</span>
        <span className="rounded bg-violet-100 px-3 py-1 text-violet-800">{data.gene}</span>
        {data.pathway.downstream.map((node) => <span key={node} className="contents"><span className="text-gray-400">→</span><span className="rounded bg-slate-100 px-3 py-1 text-slate-700">{node}</span></span>)}
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-3">
        <div>
          <h4 className="font-bold text-gray-900">可用药物／治疗</h4>
          <div className="mt-2 space-y-2">
            {data.therapies.map((item) => (
              <article key={item.therapy_key} className="rounded border p-3 text-sm">
                <div className="font-semibold">{item.name}</div>
                <div className="text-xs text-gray-500">{item.approval_status || item.therapy_type} · {item.source_name}</div>
                {item.mechanism && <p className="mt-1 line-clamp-3 text-gray-600">{item.mechanism}</p>}
              </article>
            ))}
            {data.therapies.length === 0 && <p className="text-sm text-gray-500">数据库尚无该基因的药物记录；建议类别：{data.pathway.therapy_classes.join('、') || '尚未整理'}。</p>}
          </div>
        </div>

        <div>
          <h4 className="font-bold text-gray-900">研究证据</h4>
          <div className="mt-2 space-y-2">
            {data.evidence.slice(0, 8).map((item) => (
              <article key={item.evidence_key} className="rounded border p-3 text-sm">
                <div className="font-semibold">{item.title || item.evidence_key}</div>
                <div className="text-xs text-gray-500">{item.evidence_level || 'level 未分级'} · {item.source_name}</div>
              </article>
            ))}
            {data.evidence.length === 0 && <p className="text-sm text-gray-500">尚无持久化证据。</p>}
          </div>
        </div>

        <div>
          <h4 className="font-bold text-gray-900">临床试验</h4>
          <div className="mt-2 space-y-2">
            {data.trials.slice(0, 8).map((item) => (
              <article key={item.nct_id} className="rounded border p-3 text-sm">
                <div className="font-semibold">{item.nct_id}</div>
                <div className="line-clamp-2 text-gray-600">{item.brief_title}</div>
                <div className="text-xs text-gray-500">{item.overall_status || 'status 未提供'}</div>
              </article>
            ))}
            {data.trials.length === 0 && <p className="text-sm text-gray-500">尚无匹配试验。</p>}
          </div>
        </div>
      </div>

      <p className="mt-4 border-t pt-3 text-xs text-amber-700">{data.disclaimer}</p>
    </section>
  )
}
