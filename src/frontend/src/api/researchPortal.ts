import { apiRequest } from './client'

export interface ResearchPaperPayload {
  title: string
  authors: string
  journal: string
  year: string
  doi: string
  abstract: string
  keywords: string
}

export interface ResearchUpload {
  fileName: string
  fileType: string
  fileSize: string
  uploadedAt: string
  status: 'success' | 'processing' | 'error'
}

export interface SandboxHistoryItem {
  model: string
  input: string
  output: string
  latency: string
}

export function listResearchUploads(): Promise<ResearchUpload[]> {
  return apiRequest('/research/uploads')
}

export function listSandboxHistory(): Promise<SandboxHistoryItem[]> {
  return apiRequest('/research/sandbox-history')
}

export function submitResearchPaper(payload: ResearchPaperPayload): Promise<unknown> {
  return apiRequest('/research/papers', { method: 'POST', body: JSON.stringify(payload) })
}

export function runResearchSandbox(payload: unknown): Promise<unknown> {
  return apiRequest('/predict', { method: 'POST', body: JSON.stringify(payload) })
}
