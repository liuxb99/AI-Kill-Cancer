import { apiRequest } from './client'

export interface DashboardKPI {
  label: string
  value: string
  unit: string
}

export interface DashboardKPIResponse {
  kpis: DashboardKPI[]
}

export interface CancerStatsData {
  incidence: Array<{ name: string; male: number; female: number }>
  mortality: Array<{ name: string; value: number }>
  mortality_colors: string[]
}

export interface PredictionResultsData {
  accuracy: Array<{ model: string; accuracy: number; precision: number; recall: number; f1: number }>
  roc: Array<{ fpr: number; tpr1: number; tpr2: number; tpr3: number }>
}

export interface ResearchTrendsData {
  publications: Array<{
    year: string
    deepLearning: number
    genomics: number
    immunotherapy: number
    radiomics: number
  }>
  funding: Array<{ year: string; government: number; private: number }>
}

export function getDashboardKPIs(): Promise<DashboardKPIResponse> {
  return apiRequest('/dashboard/kpis')
}

export function getCancerStats(): Promise<CancerStatsData> {
  return apiRequest('/charts/cancer-stats')
}

export function getPredictionResults(): Promise<PredictionResultsData> {
  return apiRequest('/charts/prediction-results')
}

export function getResearchTrends(): Promise<ResearchTrendsData> {
  return apiRequest('/charts/research-trends')
}
