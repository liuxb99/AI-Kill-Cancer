import { apiRequest } from './client'
import { getPTCDataQuality, type PTCDataQualityOverview } from './ptcDataQuality'
import {
  getPTCReadiness,
  getPTCSourceStatus,
  type PTCReadinessResult,
  type PTCSourceStatus,
} from './ptcCompletion'

export interface PlatformHealth {
  mode: string
  version: string
  model_loaded: boolean
  database_connected?: boolean
}

export interface ReadinessSection<T> {
  ok: boolean
  data?: T
  error?: string
}

export interface ProductionReadinessSnapshot {
  generated_at: string
  overall: 'ready' | 'degraded' | 'blocked'
  health: ReadinessSection<PlatformHealth>
  ptc: ReadinessSection<PTCReadinessResult>
  source_status: ReadinessSection<PTCSourceStatus>
  data_quality: ReadinessSection<PTCDataQualityOverview>
  blockers: string[]
  warnings: string[]
}

async function settle<T>(promise: Promise<T>): Promise<ReadinessSection<T>> {
  try {
    return { ok: true, data: await promise }
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : String(error) }
  }
}

export async function loadProductionReadiness(): Promise<ProductionReadinessSnapshot> {
  const [health, ptc, sourceStatus, dataQuality] = await Promise.all([
    settle(apiRequest<PlatformHealth>('/health')),
    settle(getPTCReadiness()),
    settle(getPTCSourceStatus()),
    settle(getPTCDataQuality(false)),
  ])

  const blockers: string[] = []
  const warnings: string[] = []

  if (!health.ok) blockers.push(`API health unavailable: ${health.error}`)
  if (health.data && health.data.database_connected === false) blockers.push('Database connection is unavailable')
  if (health.data && !health.data.model_loaded) warnings.push('Model is not loaded')

  if (!ptc.ok) blockers.push(`PTC readiness unavailable: ${ptc.error}`)
  if (ptc.data) {
    blockers.push(...ptc.data.blockers)
    warnings.push(...ptc.data.research_gaps)
  }

  if (!sourceStatus.ok) warnings.push(`PTC source status unavailable: ${sourceStatus.error}`)
  if (!dataQuality.ok) warnings.push(`PTC data quality unavailable: ${dataQuality.error}`)
  if (dataQuality.data) {
    if (dataQuality.data.summary.missing_sources > 0) {
      blockers.push(`${dataQuality.data.summary.missing_sources} required data source(s) are missing`)
    }
    if (dataQuality.data.summary.stale_sources > 0) {
      warnings.push(`${dataQuality.data.summary.stale_sources} data source(s) are stale`)
    }
    if (dataQuality.data.summary.quality_issues > 0) {
      warnings.push(`${dataQuality.data.summary.quality_issues} data quality issue(s) require review`)
    }
  }

  const uniqueBlockers = Array.from(new Set(blockers.filter(Boolean)))
  const uniqueWarnings = Array.from(new Set(warnings.filter(Boolean)))
  const overall = uniqueBlockers.length > 0
    ? 'blocked'
    : uniqueWarnings.length > 0
      ? 'degraded'
      : 'ready'

  return {
    generated_at: new Date().toISOString(),
    overall,
    health,
    ptc,
    source_status: sourceStatus,
    data_quality: dataQuality,
    blockers: uniqueBlockers,
    warnings: uniqueWarnings,
  }
}
