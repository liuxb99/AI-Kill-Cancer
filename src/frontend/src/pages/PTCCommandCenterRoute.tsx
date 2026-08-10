import { useSearchParams } from 'react-router-dom'

import DemoContextBanner, { useDemoContext } from '../components/DemoContextBanner'
import PTCCommandCenterPage from './PTCCommandCenterPage'

export default function PTCCommandCenterRoute() {
  const [searchParams] = useSearchParams()
  const { synthetic, context, loading, error } = useDemoContext()
  const caseKey = searchParams.get('demo_case')

  if (!synthetic) return <PTCCommandCenterPage />

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-primary-600">PTC Synthetic Command Center</p>
        <h1 className="text-3xl font-bold">甲狀腺乳突癌 Demo 總控台</h1>
        <p className="mt-2 text-gray-600">
          Synthetic 模式只展示 bundled demo case 的資料契約與研究鏈，不執行 TCGA、ClinicalTrials.gov、PubMed、CIViC 或其他外部同步。
        </p>
      </section>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}
      {loading ? (
        <div className="rounded border bg-white p-8 text-center text-gray-500">載入 Demo Command Center…</div>
      ) : context ? (
        <>
          <DemoContextBanner context={context} label="PTC Command Center Synthetic Demo" />
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Demo Case" value={context.case_key} />
            <Metric label="Cancer Type" value={context.cancer_type || '—'} />
            <Metric label="Variant" value={`${context.variant.gene || '—'} ${context.variant.hgvs_p || ''}`.trim()} />
            <Metric label="Evidence" value={context.evidence.level || '—'} />
          </section>

          <section className="mt-6 grid gap-6 lg:grid-cols-3">
            <Panel title="Case → Variant">
              <Info label="Case" value={context.case_key} />
              <Info label="Stage" value={context.stage} />
              <Info label="Radioiodine" value={context.radioiodine_status} />
              <Info label="Gene" value={context.variant.gene} />
              <Info label="Variant Type" value={context.variant.variant_type} />
              <Info label="Driver" value={context.variant.driver_status} />
            </Panel>
            <Panel title="Evidence → Drug">
              <Info label="Evidence Level" value={context.evidence.level} />
              <Info label="Direction" value={context.evidence.direction} />
              <Info label="Drug" value={context.drug.name} />
              <Info label="Mechanism" value={context.drug.mechanism} />
              <p className="mt-3 text-sm text-gray-600">{context.evidence.summary || 'Synthetic evidence summary unavailable.'}</p>
            </Panel>
            <Panel title="Publication → Trial">
              <Info label="Publication" value={context.publication.title} />
              <Info label="Journal" value={context.publication.journal} />
              <Info label="Trial" value={context.clinical_trial.id} />
              <Info label="Status" value={context.clinical_trial.status} />
              <Info label="Title" value={context.clinical_trial.title} />
            </Panel>
          </section>

          <section className="mt-6 rounded-xl border border-indigo-200 bg-indigo-50 p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Synthetic Isolation</p>
            <h2 className="mt-1 text-lg font-bold">外部同步与正式研究数据库操作已停用</h2>
            <p className="mt-2 text-sm text-indigo-900">
              当前 URL 的 demo_case={caseKey || context.case_key}。此模式不会调用完整同步、readiness、outcome 或 complete graph API，避免 Demo Showcase 对外部网络和正式数据产生依赖。
            </p>
          </section>
        </>
      ) : (
        <div className="rounded border bg-white p-8 text-gray-500">找不到指定 Demo Case。</div>
      )}
    </main>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 font-bold text-gray-900">{value}</div></div>
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-lg border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">{title}</h2><div className="mt-3 space-y-3">{children}</div></section>
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return <div><div className="text-xs text-gray-500">{label}</div><div className="font-medium text-gray-900">{value || '—'}</div></div>
}
