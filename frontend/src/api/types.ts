export interface Article {
  id: number
  tdx_id: number
  title: string
  body: string
  category_id: number | null
  category_name: string | null
  modified_at: string | null
  heuristic_score: number
  status: string
  tdx_url?: string
}

export interface AnalysisResult {
  id: number
  article_id: number
  overall_score: number
  score_clarity: number
  score_completeness: number
  score_findability: number
  score_redundancy: number
  score_accuracy: number
  issue_summary: string
  defects: string[]
  proposed_body: string
  approval_tier: 'auto' | 'confirm' | 'admin'
  analyzed_at: string | null
}

export interface QueueItem {
  id: number
  article_id: number
  analysis_id: number
  status: 'pending' | 'approved' | 'rejected' | 'skipped'
  queued_at: string | null
  reviewed_at: string | null
  reviewer_note: string | null
  article: Article
  analysis: AnalysisResult
}

export interface ScanJob {
  id: number
  mode: 'heuristic' | 'full_batch'
  status: 'running' | 'complete' | 'failed'
  started_at: string | null
  completed_at: string | null
  articles_scanned: number
  articles_flagged: number
  error: string | null
}

export interface AuditEntry {
  id: number
  tdx_id: number
  article_id: number
  action: string
  original_body: string | null
  new_body: string | null
  pushed_at: string | null
  tdx_url: string
}
