import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

function staticAppRoutes(source: string): string[] {
  return Array.from(source.matchAll(/<Route\s+path="([^"]+)"/g), (match) => match[1])
    .filter((route) => !route.includes(':'))
    .sort()
}

function smokeRoutes(source: string): string[] {
  const arrayBody = source.match(/export const routes = \[([\s\S]*?)\n\]/)?.[1] ?? ''
  return Array.from(arrayBody.matchAll(/['"]([^'"]+)['"]/g), (match) => match[1].split('?')[0])
    .sort()
}

describe('production route smoke coverage', () => {
  it('covers every static React route registered in App.tsx', () => {
    const app = readFileSync('./src/App.tsx', 'utf8')
    const smoke = readFileSync('./scripts/smoke-routes.mjs', 'utf8')

    expect(smokeRoutes(smoke)).toEqual(staticAppRoutes(app))
  })

  it('keeps a deep-link smoke case for the stateful PTC 3D explorer', () => {
    const smoke = readFileSync('./scripts/smoke-routes.mjs', 'utf8')

    expect(smoke).toContain('/ptc-3d?case=TCGA-SMOKE&gene=BRAF&view=literature')
  })
})
