import { useEffect, useState } from 'react'

import { getPTCDataQuality, type PTCDataQualityOverview } from '../api/ptcDataQuality'

export default function PTCDataQualityPage() {
  const [data, setData] = useState<PTCDataQualityOverview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [staleOnly, setStaleOnly] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    void getPTCDataQuality(staleOnly)
      .then(setData)
      .catch((reason) => setError(reason instanceof Error ? reason.message : '无法载入资料品质状态'))
      .finally(() => setLoading(false))
  }, [staleOnly])

  const displayedGenes = data?.gene_coverage.slice(0, 100) || []

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-emerald-600">PTC Data Provenance & Freshness Center</p>
        <h1 className="text-3xl font-bold">资料来源、版本、新鲜度与覆盖缺口</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          页面直接展示数据库中的来源状态与前 100 笔基因覆盖资料，不需要输入查询条件。
        </p>
      </header>

      <div className="mb-5 flex flex-wrap items-center justify-between gap-4 rounded-xl border bg-white p-4 shadow-sm">
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={staleOnly} onChange={(event) => setStaleOnly(event.target.checked)} />
          只显示过期或缺失来源
        </label>
        <div className="text-sm text-gray-500">数据库基因覆盖：展示 {displayedGenes.length} / {data?.gene_coverage.length || 0} 笔</div>
      </div>

      {loading && <div className="rounded border bg-white p-6 text-gray-500">正在稽核资料来源…</div>}
      {error && <div className="rounded border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {data && !loading && (
        <div className="space-y-6">
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <Metric label="Fresh sources" value={data.summary.fresh_sources} />
            <Metric label="Stale sources" value={data.summary.stale_sources} />
            <Metric label="Missing sources" value={data.summary.missing_sources} />
            <Metric label="Quality issues" value={data.summary.quality_issues} />
            <Metric label="Genes with gaps" value={data.summary.genes_with_gaps} />
          </section>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.sources.map((source) => (
              <article key={source.source_name} className="rounded-xl border bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-bold">{source.label}</h2>
                    <p className="text-xs text-gray-500">{source.data_role}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-bold ${freshnessClass(source.freshness)}`}>{source.freshness}</span>
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <DataPoint label="Records" value={source.record_count} />
                  <DataPoint label="Age days" value={source.age_days ?? '—'} />
                  <DataPoint label="Missing URL" value={source.missing_source_url} />
                  <DataPoint label="Missing version" value={source.missing_source_version} />
                  <DataPoint label="Incomplete batches" value={source.failed_or_incomplete_batches} />
                  <DataPoint label="Policy threshold" value={`${source.stale_after_days} d`} />
                </dl>
                <p className="mt-3 break-all text-xs text-gray-500">{source.last_retrieved_at || 'No persisted retrieval timestamp'}</p>
                <a className="mt-3 inline-block text-sm font-semibold text-emerald-700" href={source.homepage} target="_blank" rel="noreferrer">打开来源主页 ↗</a>
              </article>
            ))}
          </section>

          <section className="rounded-xl border bg-white p-5 shadow-sm">
            <h2 className="text-xl font-bold">持久化资料库存</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
              {Object.entries(data.inventory).map(([name, value]) => <Metric key={name} label={name} value={value} />)}
            </div>
          </section>

          <section className="overflow-hidden rounded-xl border bg-white shadow-sm">
            <div className="border-b p-5">
              <h2 className="text-xl font-bold">数据库前 100 笔基因覆盖矩阵</h2>
              <p className="text-sm text-gray-500">4 分代表同时具备病例变异、药物靶点、Evidence 与 Clinical Trial。</p>
            </div>
            <div className="max-h-[700px] overflow-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-xs uppercase text-gray-500">
                  <tr><th className="px-4 py-3">Gene</th><th className="px-4 py-3">Score</th><th className="px-4 py-3">Variants</th><th className="px-4 py-3">Targets</th><th className="px-4 py-3">Evidence</th><th className="px-4 py-3">Trials</th><th className="px-4 py-3">Gaps</th></tr>
                </thead>
                <tbody>
                  {displayedGenes.map((row) => (
                    <tr key={row.gene} className="border-t">
                      <td className="px-4 py-3 font-bold">{row.gene}</td>
                      <td className="px-4 py-3">{row.coverage_score}/4</td>
                      <td className="px-4 py-3">{row.case_variants}</td>
                      <td className="px-4 py-3">{row.therapy_targets}</td>
                      <td className="px-4 py-3">{row.evidence_records}</td>
                      <td className="px-4 py-3">{row.clinical_trials}</td>
                      <td className="px-4 py-3 text-amber-700">{row.gaps.length ? row.gaps.join(' · ') : 'complete'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {data.issues.length > 0 && (
            <section className="rounded-xl border border-amber-200 bg-amber-50 p-5">
              <h2 className="font-bold text-amber-950">客观资料问题</h2>
              <ul className="mt-3 space-y-2 text-sm text-amber-900">
                {data.issues.map((issue, index) => <li key={`${issue.source}-${issue.code}-${index}`}>{issue.severity.toUpperCase()} · {issue.source} · {issue.code}{issue.count ? ` · ${issue.count}` : ''}</li>)}
              </ul>
            </section>
          )}

          <section className="rounded-xl border bg-slate-900 p-5 text-sm text-slate-200">
            <strong>稽核说明：</strong> {data.policy_note}
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              {data.trace.map((step) => <span key={step.step} className="rounded bg-slate-800 px-2 py-1">{step.step}. {step.name}: {step.records}</span>)}
            </div>
          </section>
        </div>
      )}
    </main>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-xl border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-2xl font-bold">{value}</div></div>
}

function DataPoint({ label, value }: { label: string; value: string | number }) {
  return <div><dt className="text-xs text-gray-400">{label}</dt><dd className="font-semibold">{value}</dd></div>
}

function freshnessClass(status: string): string {
  if (status === 'fresh') return 'bg-emerald-100 text-emerald-800'
  if (status === 'stale') return 'bg-amber-100 text-amber-800'
  return 'bg-rose-100 text-rose-800'
}
