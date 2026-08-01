const API_BASE = import.meta.env.VITE_API_URL || ''

export interface PTCPublicationFigure {
  figure_id?: string
  label?: string
  caption?: string
  image_url?: string
  source_href?: string
}

export interface PTCPublicationTable {
  table_id?: string
  label?: string
  caption?: string
  headers: string[]
  rows: string[][]
  row_count: number
}

export interface PTCPublication {
  pmid: string
  pmcid?: string
  title?: string
  abstract?: string
  citation?: string
  source_url?: string
  full_text_available: boolean
  full_text_url?: string
  authors: string[]
  genes: string[]
  figures: PTCPublicationFigure[]
  tables: PTCPublicationTable[]
  figure_count: number
  table_count: number
}

export interface PTCPublicationList {
  count: number
  publications: PTCPublication[]
}

export async function getPTCPublications(gene: string, limit = 20): Promise<PTCPublicationList> {
  const params = new URLSearchParams({ gene, limit: String(limit) })
  const response = await fetch(`${API_BASE}/api/v1/ptc-literature/publications?${params}`)
  if (!response.ok) throw new Error(`无法载入 ${gene} 文献图表：HTTP ${response.status}`)
  return response.json()
}
