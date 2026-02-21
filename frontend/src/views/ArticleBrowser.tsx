import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listArticles } from '../api/articles'

export default function ArticleBrowser() {
  const [search, setSearch] = useState('')
  const { data: articles, isLoading } = useQuery({
    queryKey: ['articles'],
    queryFn: () => listArticles(),
  })

  const filtered = (articles ?? []).filter(a =>
    a.title.toLowerCase().includes(search.toLowerCase()) ||
    (a.category_name ?? '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Article Browser</h1>
      <input
        placeholder="Search by title or category..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={{ padding: '8px 12px', width: 360, marginBottom: 16, fontSize: 14, border: '1px solid #e2e8f0', borderRadius: 6 }}
      />
      {isLoading && <p style={{ color: '#64748b' }}>Loading articles...</p>}
      {!isLoading && filtered.length === 0 && <p style={{ color: '#64748b' }}>No articles found.</p>}
      {filtered.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8, overflow: 'hidden', border: '1px solid #e2e8f0' }}>
          <thead>
            <tr style={{ background: '#f1f5f9' }}>
              <th style={th}>Title</th>
              <th style={th}>Category</th>
              <th style={th}>Score</th>
              <th style={th}>Status</th>
              <th style={th}>Modified</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(a => (
              <tr key={a.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                <td style={td}>{a.title}</td>
                <td style={td}>{a.category_name ?? '—'}</td>
                <td style={td}>
                  <span style={{ color: a.heuristic_score < 5 ? '#ef4444' : '#16a34a', fontWeight: 600 }}>
                    {a.heuristic_score.toFixed(1)}
                  </span>
                </td>
                <td style={td}>{a.status}</td>
                <td style={td}>{a.modified_at ? new Date(a.modified_at).toLocaleDateString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

const th: React.CSSProperties = { padding: '10px 14px', textAlign: 'left', fontWeight: 600, fontSize: 13, color: '#374151' }
const td: React.CSSProperties = { padding: '10px 14px', fontSize: 14, color: '#1e293b' }
