import ReactDiffViewer from 'react-diff-viewer-continued'
import type { QueueItem } from '../api/types'

interface Props {
  item: QueueItem
  onApprove: (id: number, editedBody?: string) => void
  onReject: (id: number, note: string) => void
  onSkip: (id: number) => void
}

const tierColor: Record<string, string> = {
  auto: '#16a34a',
  confirm: '#d97706',
  admin: '#dc2626',
}

export default function DiffReview({ item, onApprove, onReject, onSkip }: Props) {
  const defects: string[] = (() => {
    try { return JSON.parse(item.analysis.defects_json) } catch { return [] }
  })()

  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 24, marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <h2 style={{ margin: '0 0 4px' }}>{item.article.title}</h2>
          <span style={{ fontSize: 13, color: '#64748b' }}>
            {item.article.category_name ?? 'Uncategorized'} &nbsp;|&nbsp;
            Overall: <strong>{item.analysis.overall_score.toFixed(1)}</strong>
          </span>
        </div>
        <span style={{
          background: tierColor[item.analysis.approval_tier] ?? '#64748b',
          color: '#fff', padding: '4px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600,
        }}>
          {item.analysis.approval_tier.toUpperCase()}
        </span>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
        {(['clarity','completeness','findability','redundancy','accuracy'] as const).map(dim => (
          <div key={dim} style={{ textAlign: 'center', minWidth: 70 }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: (item.analysis[`score_${dim}`] as number) < 6 ? '#ef4444' : '#16a34a' }}>
              {(item.analysis[`score_${dim}`] as number).toFixed(1)}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', textTransform: 'capitalize' }}>{dim}</div>
          </div>
        ))}
      </div>

      <p style={{ color: '#374151', marginBottom: 8 }}><strong>Issues:</strong> {item.analysis.issue_summary}</p>
      {defects.length > 0 && (
        <ul style={{ color: '#6b7280', fontSize: 13, marginBottom: 16 }}>
          {defects.map((d, i) => <li key={i}>{d}</li>)}
        </ul>
      )}

      <ReactDiffViewer
        oldValue={item.article.body}
        newValue={item.analysis.proposed_body}
        splitView={true}
        leftTitle="Current"
        rightTitle="Proposed"
      />

      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        <button onClick={() => onApprove(item.id)}
          style={{ padding: '8px 20px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
          Approve
        </button>
        <button onClick={() => {
          const note = window.prompt('Rejection reason (optional):') ?? ''
          onReject(item.id, note)
        }}
          style={{ padding: '8px 20px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
          Reject
        </button>
        <button onClick={() => onSkip(item.id)}
          style={{ padding: '8px 20px', background: '#64748b', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
          Skip
        </button>
      </div>
    </div>
  )
}
