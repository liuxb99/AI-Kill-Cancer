import { apiRequest, withQuery } from './client'

export interface WorkspaceStatus {
  app_mode: string
  backend: string
  local_first: boolean
  persistent: boolean
  database_path: string | null
  exists: boolean | null
  size_bytes?: number
  import_history_path?: string
}

export interface DuplicateEntityPreview {
  total: number
  existing: number
  new: number
  existing_keys: string[]
  new_keys: string[]
}

export interface ImportPreview {
  source_dir: string
  validation: { ok: boolean; errors: string[] }
  counts: Record<string, number>
  import_scope: string[]
  duplicates: Record<string, DuplicateEntityPreview> | null
  overwrite_existing: boolean
  requires_confirmation: boolean
  confirmation_token: string
}

export interface ImportCommitResult {
  ok: boolean
  source_dir: string
  imported: Record<string, number>
  duplicates: Record<string, DuplicateEntityPreview> | null
  overwrite_existing: boolean
  history_path: string
  message: string
}

export interface ImportHistoryItem {
  timestamp?: string
  source_dir?: string
  imported?: Record<string, number>
  duplicates?: Record<string, DuplicateEntityPreview> | null
  overwrite_existing?: boolean
  app_mode?: string
  database_path?: string
}

export async function getWorkspaceStatus(): Promise<WorkspaceStatus> {
  return apiRequest<WorkspaceStatus>('/workspace/status')
}

export async function previewWorkspaceImport(sourceDir: string): Promise<ImportPreview> {
  return apiRequest<ImportPreview>('/workspace/import/csv/preview', {
    method: 'POST',
    body: JSON.stringify({ source_dir: sourceDir }),
  })
}

export async function commitWorkspaceImport(sourceDir: string): Promise<ImportCommitResult> {
  return apiRequest<ImportCommitResult>('/workspace/import/csv/commit', {
    method: 'POST',
    body: JSON.stringify({ source_dir: sourceDir, confirm: 'IMPORT' }),
  })
}

export async function getWorkspaceImportHistory(limit = 50): Promise<{ items: ImportHistoryItem[]; history_path: string }> {
  return apiRequest(withQuery('/workspace/import/history', { limit }))
}
