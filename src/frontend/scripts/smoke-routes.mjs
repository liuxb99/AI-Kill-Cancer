const baseUrl = process.env.SMOKE_BASE_URL || 'http://127.0.0.1:4173'

export const routes = [
  '/',
  '/knowledge',
  '/tools',
  '/research',
  '/dashboard',
  '/research-portal',
  '/workbench',
  '/production-readiness',
  '/ptc-command-center',
  '/ptc-data-quality',
  '/ptc-snapshots',
  '/ptc-3d?case=TCGA-SMOKE&gene=BRAF&view=literature',
  '/ptc-timeline',
  '/ptc-trial-matching',
  '/ptc-evidence-matrix',
  '/ptc-cohort',
  '/ptc-assistant',
  '/ptc-reports',
  '/ptc-workbench',
  '/ptc-research',
  '/ptc-knowledge',
  '/recommendation',
  '/clinical-decision',
  '/tumor-board',
  '/clinical-graph',
  '/treatment-plans',
  '/treatment-plans/new',
]

const failures = []

for (const route of routes) {
  const url = new URL(route, baseUrl)
  try {
    const response = await fetch(url, { redirect: 'manual' })
    const body = await response.text()
    const contentType = response.headers.get('content-type') || ''
    const isHtml = contentType.includes('text/html') && body.includes('<div id="root"></div>')
    if (!response.ok || !isHtml) {
      failures.push(`${route}: HTTP ${response.status}, content-type=${contentType}`)
      continue
    }
    console.log(`OK ${response.status} ${route}`)
  } catch (error) {
    failures.push(`${route}: ${error instanceof Error ? error.message : String(error)}`)
  }
}

if (failures.length) {
  console.error('\nProduction route smoke failures:')
  failures.forEach((failure) => console.error(`- ${failure}`))
  process.exit(1)
}

console.log(`\nValidated ${routes.length} production routes.`)
