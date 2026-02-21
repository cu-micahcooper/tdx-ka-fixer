import client from './client'
import type { AuditEntry } from './types'

export interface ApprovedChange {
  id: number
  article_id: number
  article_title: string | null
  tdx_id: number | null
  push_status: 'pending' | 'success' | 'failed'
  push_error: string | null
  approved_at: string | null
  pushed_at: string | null
}

export const listApproved = () =>
  client.get<ApprovedChange[]>('/approved').then(r => r.data)

export const pushAll = () =>
  client.post<AuditEntry[]>('/approved/push-all').then(r => r.data)

export const pushOne = (id: number) =>
  client.post<AuditEntry>(`/approved/${id}/push`).then(r => r.data)
