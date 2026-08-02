import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import {
  loadProductionReadiness,
  type ProductionReadinessSnapshot,
  type ReadinessSection,
} from '../api/productionReadiness'

function badge(status: 'ready' | 'degraded' | 'blocked') {
  if (status === 'ready') return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  if (status === 'degraded') return 'border-amber-200 bg-amber-50 text-amber-700'
  return 'border-red-200 bg-red-50 text-red-700'
}

function sectionLabel(section: ReadinessSection<unknown>) {
  return section.ok ? '可读取' : '不可读取'
}

export default function ProductionReadinessPage() {
  const navigate = useNavigate()
  const [snapshot, setSnapshot] = useState<ProductionReadinessSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      setSnapshot(await loadProductionReadiness())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法生成生产就绪快照')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  const counts = useMemo(() => snapshot?.source_status.data || null, [snapshot])
  const quality = snapshot?.data_quality.data
  const ptc = snapshot?.ptc.data
  const health = snapshot?.health.data

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-sky-600">Production Readiness Center</p>
          <h1 className="mt-1 text-3xl font-bold text-gray-900">生产就绪中心</h1>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-gray-600">
            集中检查 API、数据库、模型、PTC 数据完整度、知识图谱结构、来源新鲜度与研究阻塞项。
            此页面用于系统运维与研究资料准备度判断，不代表临床有效性或医疗许可。
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => navigate('/ptc-command-center')} className="rounded border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">
            PTC 总控台
          </button>
          <button onClick={() => void refresh()} disabled={loading} className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50">
            {loading ? '检查中…' : '重新检查'}
          </button>
        </div>
      </section>

      {error && <div className="rounded border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {loading && !snapshot && (
        <div className="rounded-xl border bg-white p-12 text-center text-gray-500 shadow-sm">正在收集生产就绪状态…</div>
      )}

      {snapshot && (
        <>
          <section className={`rounded-xl border p-5 shadow-sm ${badge(snapshot.overall)}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider">Overall status</div>
                <div className="mt-1 text-2xl font-bold">
                  {snapshot.overall === 'ready' ? '已就绪' : snapshot.overall === 'degraded' ? '部分就绪' : '尚未就绪'}
                </div>
              </div>
              <div className="text-sm">生成时间：{new Date(snapshot.generated_at).toLocaleString()}</div>
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatusCard title="API / Runtime" ok={snapshot.health.ok} value={health?.mode || sectionLabel(snapshot.health)} detail={`版本 ${health?.version || '—'}`} />
            <StatusCard title="数据库" ok={health?.database_connected !== false && snapshot.health.ok} value={health?.database_connected === false ? '未连接' : snapshot.health.ok ? '已连接／未回报异常' : '未知'} detail="由 /health 提供" />
            <StatusCard title="模型" ok={Boolean(health?.model_loaded)} value={health?.model_loaded ? '已载入' : '未载入'} detail="影响预测功能，不影响静态研究资料浏览" />
            <StatusCard title="PTC Research" ok={ptc?.status === 'ready'} value={ptc?.status === 'ready' ? 'Research Ready' : 'Not Ready'} detail="完整度与知识图谱结构检查" />
          </section>

          <section className="grid gap-5 lg:grid-cols-2">
            <IssuePanel title="阻塞项" items={snapshot.blockers} empty="目前没有阻塞项" tone="red" />
            <IssuePanel title="警告与研究缺口" items={snapshot.warnings} empty="目前没有警告" tone="amber" />
          </section>

          <section className="rounded-xl border bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-gray-900">PTC 数据库存量</h2>
                <p className="text-sm text-gray-500">当前持久化资料数量，不代表证据质量。</p>
              </div>
              <button onClick={() => navigate('/ptc-data-quality')} className="text-sm font-semibold text-sky-700 hover:underline">打开资料质量中心 →</button>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {counts ? Object.entries(counts).filter(([, value]) => typeof value === 'number').map(([key, value]) => (
                <Metric key={key} label={key.replace(/_/g, ' ')} value={value as number} />
              )) : <div className="text-sm text-gray-500">资料状态不可读取：{snapshot.source_status.error || '未知错误'}</div>}
            </div>
          </section>

          <section className="rounded-xl border bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold text-gray-900">来源新鲜度</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[780px] text-sm">
                <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                  <tr><th className="px-3 py-2">来源</th><th className="px-3 py-2">状态</th><th className="px-3 py-2">记录</th><th className="px-3 py-2">最近取得</th><th className="px-3 py-2">问题</th></tr>
                </thead>
                <tbody className="divide-y">
                  {(quality?.sources || []).map((source) => (
                    <tr key={source.source_name}>
                      <td className="px-3 py-3 font-semibold text-gray-800">{source.label}</td>
                      <td className="px-3 py-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${source.freshness === 'fresh' ? 'bg-emerald-100 text-emerald-700' : source.freshness === 'stale' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>{source.freshness}</span></td>
                      <td className="px-3 py-3">{source.record_count}</td>
                      <td className="px-3 py-3 text-gray-500">{source.last_retrieved_at ? new Date(source.last_retrieved_at).toLocaleString() : '—'}</td>
                      <td className="px-3 py-3 text-gray-500">{source.failed_or_incomplete_batches + source.missing_source_url + source.missing_source_version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!quality && <div className="py-6 text-sm text-gray-500">资料质量不可读取：{snapshot.data_quality.error || '未知错误'}</div>}
            </div>
          </section>

          {ptc && (
            <section className="rounded-xl border bg-white p-5 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900">知识图谱结构检查</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <Metric label="Nodes" value={ptc.graph.nodes} />
                <Metric label="Relations" value={ptc.graph.relations} />
                <Metric label="Dangling edges" value={ptc.graph.dangling_edge_count} />
                <Metric label="KnowGraph entities" value={ptc.graph.knowgraph_entities} />
                <Metric label="KnowGraph relations" value={ptc.graph.knowgraph_relations} />
              </div>
            </section>
          )}
        </>
      )}
    </main>
  )
}

function StatusCard({ title, ok, value, detail }: { title: string; ok: boolean; value: string; detail: string }) {
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3"><span className="text-sm font-semibold text-gray-600">{title}</span><span className={`h-2.5 w-2.5 rounded-full ${ok ? 'bg-emerald-500' : 'bg-red-500'}`} /></div>
      <div className="mt-3 text-xl font-bold text-gray-900">{value}</div>
      <div className="mt-1 text-xs text-gray-500">{detail}</div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border bg-gray-50 p-3"><div className="text-xs uppercase tracking-wide text-gray-500">{label}</div><div className="mt-1 text-2xl font-bold text-gray-900">{value.toLocaleString()}</div></div>
}

function IssuePanel({ title, items, empty, tone }: { title: string; items: string[]; empty: string; tone: 'red' | 'amber' }) {
  const classes = tone === 'red' ? 'border-red-200 bg-red-50 text-red-800' : 'border-amber-200 bg-amber-50 text-amber-800'
  return <section className={`rounded-xl border p-5 ${classes}`}><h2 className="font-bold">{title}</h2>{items.length ? <ul className="mt-3 space-y-2 text-sm">{items.map((item) => <li key={item}>• {item}</li>)}</ul> : <div className="mt-3 text-sm">{empty}</div>}</section>
}
