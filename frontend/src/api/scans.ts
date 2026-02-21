import client from './client'
import type { ScanJob } from './types'

export const listScans = () =>
  client.get<ScanJob[]>('/scans').then(r => r.data)

export const triggerScan = (mode: 'heuristic' | 'full_batch') =>
  client.post<ScanJob>('/scans/trigger', { mode }).then(r => r.data)
