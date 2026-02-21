import client from './client'

export interface StatusStat {
  tdx_status: number | null
  label: string
  count: number
  avg_score: number | null
  needs_review: number
}

export interface VisibilityStat {
  is_public: boolean
  label: string
  count: number
  avg_score: number | null
  needs_review: number
}

export interface CategoryStat {
  category_name: string
  count: number
  avg_score: number | null
  needs_review: number
}

export interface DashboardStats {
  total_articles: number
  avg_heuristic_score: number | null
  needs_review_count: number
  by_publish_status: StatusStat[]
  by_visibility: VisibilityStat[]
  by_category: CategoryStat[]
}

export const getStats = () =>
  client.get<DashboardStats>('/stats').then(r => r.data)
