import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listScans, triggerScan } from '../api/scans'
import { listQueue } from '../api/queue'

export default function Dashboard() {
  const qc = useQueryClient()
  const { data: scans } = useQuery({ queryKey: ['scans'], queryFn: listScans })
  const { data: pending } = useQuery({ queryKey: ['queue', 'pending'], queryFn: () => listQueue('pending') })
  const { data: approved } = useQuery({ queryKey: ['queue', 'approved'], queryFn: () => listQueue('approved') })

  const trigger = useMutation({
    mutationFn: triggerScan,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scans'] }),
  })

  const lastScan = scans?.[0]

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        <StatCard label="Pending Review" value={pending?.length ?? 0} />
        <StatCard label="Approved (not pushed)" value={approved?.length ?? 0} />
        <StatCard label="Total Scans" value={scans?.length ?? 0} />
      </div>

      <section style={{ marginBottom: 24 }}>
        <h2>Last Scan</h2>
        {lastScan ? (
          <p style={{ color: '#374151' }}>
            Mode: <strong>{lastScan.mode}</strong> &nbsp;|&nbsp;
            Status: <strong style={{ color: lastScan.status === 'failed' ? '#dc2626' : '#16a34a' }}>{lastScan.status}</strong> &nbsp;|&nbsp;
            Scanned: {lastScan.articles_scanned} &nbsp;|&nbsp;
            Flagged: {lastScan.articles_flagged} &nbsp;|&nbsp;
            At: {lastScan.started_at ? new Date(lastScan.started_at).toLocaleString() : '—'}
          </p>
        ) : <p style={{ color: '#64748b' }}>No scans yet.</p>}
      </section>

      <section>
        <h2>Trigger Scan</h2>
        <button
          onClick={() => trigger.mutate('heuristic')}
          disabled={trigger.isPending}
          style={{ marginRight: 12, padding: '8px 20px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}
        >
          Run Heuristic Scan
        </button>
        <button
          onClick={() => trigger.mutate('full_batch')}
          disabled={trigger.isPending}
          style={{ padding: '8px 20px', background: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}
        >
          Run Full Batch Scan
        </button>
        {trigger.isPending && <span style={{ marginLeft: 12, color: '#64748b' }}>Running...</span>}
        {trigger.isError && <span style={{ marginLeft: 12, color: '#dc2626' }}>Scan failed.</span>}
      </section>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8,
      padding: '16px 24px', minWidth: 160, textAlign: 'center',
    }}>
      <div style={{ fontSize: 32, fontWeight: 700, color: '#1e293b' }}>{value}</div>
      <div style={{ color: '#64748b', fontSize: 13 }}>{label}</div>
    </div>
  )
}
