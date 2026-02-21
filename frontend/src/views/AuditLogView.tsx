import { useQuery } from '@tanstack/react-query'
import { listAudit } from '../api/audit'

export default function AuditLogView() {
  const { data: entries, isLoading } = useQuery({
    queryKey: ['audit'],
    queryFn: () => listAudit(100),
  })

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Audit Log</h1>
      {isLoading && <p style={{ color: '#64748b' }}>Loading...</p>}
      {!isLoading && (entries?.length === 0) && <p style={{ color: '#64748b' }}>No changes pushed yet.</p>}
      {(entries?.length ?? 0) > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
          <thead>
            <tr style={{ background: '#f1f5f9' }}>
              <th style={th}>TDX ID</th>
              <th style={th}>Action</th>
              <th style={th}>Pushed At</th>
            </tr>
          </thead>
          <tbody>
            {entries?.map(e => (
              <tr key={e.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                <td style={td}>{e.tdx_id}</td>
                <td style={td}>{e.action}</td>
                <td style={td}>{e.pushed_at ? new Date(e.pushed_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

const th: React.CSSProperties = { padding: '10px 14px', textAlign: 'left', fontWeight: 600, fontSize: 13, color: '#374151' }
const td: React.CSSProperties = { padding: '10px 14px', fontSize: 14 }
