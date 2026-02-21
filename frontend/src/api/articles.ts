import client from './client'
import type { Article, AnalysisResult } from './types'

export interface ArticleDetail {
  article: Article & { view_count: number; last_synced_at: string | null }
  analysis: AnalysisResult | null
  queue_item: { id: number; status: string; reviewer_note: string | null } | null
}

export const listArticles = (params?: { status?: string; category_id?: number }) =>
  client.get<Article[]>('/articles', { params }).then(r => r.data)

export const getArticle = (id: number) =>
  client.get<Article>(`/articles/${id}`).then(r => r.data)

export const getArticleAnalysis = (id: number) =>
  client.get<ArticleDetail>(`/articles/${id}/analysis`).then(r => r.data)
