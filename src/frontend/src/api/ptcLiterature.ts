import { apiRequest, withQuery } from './client'

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

export function getPTCPublications(gene: string, limit = 20): Promise<PTCPublicationList> {
  return apiRequest(withQuery('/ptc-literature/publications', { gene, limit }))
}
