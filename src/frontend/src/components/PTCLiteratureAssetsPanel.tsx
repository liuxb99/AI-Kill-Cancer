import { useEffect, useState } from 'react'

import { getPTCPublications, type PTCPublication } from '../api/ptcLiterature'

export default function PTCLiteratureAssetsPanel({ gene }: { gene: string | null }) {
  const [publications, setPublications] = useState<PTCPublication[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!gene) {
      setPublications([])
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    void getPTCPublications(gene)
      .then((result) => {
        if (!cancelled) setPublications(result.publications)
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : '无法载入文献图表')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [gene])

  if (!gene) return null

  return (
    <section className="rounded-xl border bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Publication Evidence Assets</p>
          <h3 className="text-xl font-bold text-gray-900">{gene} 文献图表证据</h3>
          <p className="text-sm text-gray-500">PubMed 摘要与 PMC 开放全文中的 Figure／Table。</p>
        </div>
        <span className="rounded bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">{publications.length} publications</span>
      </div>

      {loading && <div className="mt-4 text-sm text-gray-500">载入 {gene} 文献资产…</div>}
      {error && <div className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {!loading && !error && publications.length === 0 && (
        <div className="mt-4 rounded border border-dashed p-5 text-sm text-gray-500">尚无该基因的 PubMed Evidence。请先在 PTC 总控台同步 PubMed。</div>
      )}

      <div className="mt-4 space-y-4">
        {publications.map((publication) => (
          <details key={publication.pmid} className="overflow-hidden rounded-lg border" open={publication.full_text_available}>
            <summary className="cursor-pointer bg-slate-50 px-4 py-3">
              <div className="font-semibold text-gray-900">{publication.title || `PMID ${publication.pmid}`}</div>
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500">
                <span>PMID {publication.pmid}</span>
                {publication.pmcid && <span>{publication.pmcid}</span>}
                <span>{publication.figure_count} figures</span>
                <span>{publication.table_count} tables</span>
                {publication.citation && <span>{publication.citation}</span>}
              </div>
            </summary>

            <div className="space-y-4 p-4">
              {publication.abstract && <p className="text-sm leading-6 text-gray-600">{publication.abstract}</p>}
              <div className="flex flex-wrap gap-2 text-xs">
                {publication.source_url && <a className="rounded bg-blue-600 px-3 py-1.5 text-white" href={publication.source_url} target="_blank" rel="noreferrer">PubMed</a>}
                {publication.full_text_url && <a className="rounded bg-emerald-600 px-3 py-1.5 text-white" href={publication.full_text_url} target="_blank" rel="noreferrer">PMC 全文</a>}
              </div>

              {publication.figures.length > 0 && (
                <div>
                  <h4 className="font-bold text-gray-900">Figures</h4>
                  <div className="mt-2 grid gap-4 lg:grid-cols-2">
                    {publication.figures.map((figure, index) => (
                      <figure key={figure.figure_id || `${publication.pmid}:figure:${index}`} className="overflow-hidden rounded border bg-slate-50">
                        {figure.image_url && <img className="max-h-[420px] w-full object-contain bg-white" src={figure.image_url} alt={figure.caption || figure.label || `Figure ${index + 1}`} loading="lazy" />}
                        <figcaption className="p-3 text-sm text-gray-600">
                          <strong>{figure.label || `Figure ${index + 1}`}</strong>{figure.caption ? ` · ${figure.caption}` : ''}
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                </div>
              )}

              {publication.tables.length > 0 && (
                <div>
                  <h4 className="font-bold text-gray-900">Tables</h4>
                  <div className="mt-2 space-y-4">
                    {publication.tables.map((table, index) => (
                      <div key={table.table_id || `${publication.pmid}:table:${index}`} className="overflow-hidden rounded border">
                        <div className="bg-slate-50 px-3 py-2 text-sm text-gray-700">
                          <strong>{table.label || `Table ${index + 1}`}</strong>{table.caption ? ` · ${table.caption}` : ''}
                        </div>
                        <div className="max-h-80 overflow-auto">
                          <table className="min-w-full border-collapse text-xs">
                            {table.headers.length > 0 && (
                              <thead className="sticky top-0 bg-slate-100">
                                <tr>{table.headers.map((header, headerIndex) => <th key={headerIndex} className="border px-2 py-1.5 text-left">{header}</th>)}</tr>
                              </thead>
                            )}
                            <tbody>
                              {table.rows.map((row, rowIndex) => (
                                <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex} className="border px-2 py-1.5 align-top">{cell}</td>)}</tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!publication.full_text_available && <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">该文献没有可用的 PMC 开放全文，当前仅保存摘要证据。</p>}
            </div>
          </details>
        ))}
      </div>
    </section>
  )
}
