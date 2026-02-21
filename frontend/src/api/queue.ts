import client from './client'
import type { QueueItem } from './types'

export const listQueue = (status = 'pending') =>
  client.get<QueueItem[]>('/queue', { params: { status } }).then(r => r.data)

export const approveItem = (id: number, editedBody?: string) =>
  client.post<QueueItem>(`/queue/${id}/approve`, { edited_body: editedBody }).then(r => r.data)

export const rejectItem = (id: number, note = '') =>
  client.post<QueueItem>(`/queue/${id}/reject`, { note }).then(r => r.data)

export const skipItem = (id: number) =>
  client.post<QueueItem>(`/queue/${id}/skip`).then(r => r.data)
