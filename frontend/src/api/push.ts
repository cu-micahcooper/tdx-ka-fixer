import client from './client'
import type { AuditEntry } from './types'

export const pushAll = () =>
  client.post<AuditEntry[]>('/approved/push-all').then(r => r.data)

export const pushOne = (id: number) =>
  client.post<AuditEntry>(`/approved/${id}/push`).then(r => r.data)
