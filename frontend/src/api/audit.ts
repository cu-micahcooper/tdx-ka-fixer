import client from './client'
import type { AuditEntry } from './types'

export const listAudit = (limit = 100) =>
  client.get<AuditEntry[]>('/audit', { params: { limit } }).then(r => r.data)
