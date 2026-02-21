import client from './client'
import type { Article } from './types'

export const listArticles = (params?: { status?: string; category_id?: number }) =>
  client.get<Article[]>('/articles', { params }).then(r => r.data)

export const getArticle = (id: number) =>
  client.get<Article>(`/articles/${id}`).then(r => r.data)
