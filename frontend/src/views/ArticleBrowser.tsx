import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { listArticles } from '../api/articles'

const selectCls = 'px-3 py-2 text-sm border border-slate-200 rounded-md bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400'

const tdxStatusLabel: Record<number, string> = {
  1: 'Draft',
  2: 'Submitted',
  3: 'Published',
  5: 'Archived',
}

const tdxStatusColor: Record<number, string> = {
  1: 'bg-slate-100 text-slate-600',
  2: 'bg-amber-100 text-amber-700',
  3: 'bg-green-100 text-green-700',
  5: 'bg-red-100 text-red-700',
}

export default function ArticleBrowser() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [search, setSearch] = useState('')
  const [tdxStatusFilter, setTdxStatusFilter] = useState<string>(searchParams.get('tdx_status') ?? '')
  const [publicFilter, setPublicFilter] = useState<string>(searchParams.get('is_public') ?? '')
  const [categoryFilter, setCategoryFilter] = useState<string>(searchParams.get('category') ?? '')
  const [scoreFilter, setScoreFilter] = useState<string>(searchParams.get('score') ?? '')

  const queryParams = {
    ...(tdxStatusFilter ? { tdx_status: Number(tdxStatusFilter) } : {}),
    ...(publicFilter !== '' ? { is_public: publicFilter === 'true' } : {}),
  }

  const { data: articles, isLoading } = useQuery({
    queryKey: ['articles', tdxStatusFilter, publicFilter],
    queryFn: () => listArticles(Object.keys(queryParams).length ? queryParams : undefined),
  })

  const categories = useMemo(() => {
    const names = (articles ?? []).map(a => a.category_name).filter(Boolean) as string[]
    return Array.from(new Set(names)).sort()
  }, [articles])

  const filtered = (articles ?? []).filter(a => {
    if (search && !a.title.toLowerCase().includes(search.toLowerCase()) &&
        !(a.category_name ?? '').toLowerCase().includes(search.toLowerCase())) return false
    if (categoryFilter && a.category_name !== categoryFilter) return false
    if (scoreFilter === 'low' && a.heuristic_score >= 5) return false
    if (scoreFilter === 'high' && a.heuristic_score < 5) return false
    return true
  })

  return (
    <div>
      <h1 className="mt-0 mb-4 text-2xl font-bold text-slate-800">Article Browser</h1>
      <div className="flex gap-2 flex-wrap mb-4">
        <input
          placeholder="Search by title or category..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="px-3 py-2 text-sm border border-slate-200 rounded-md w-72 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <select value={tdxStatusFilter} onChange={e => setTdxStatusFilter(e.target.value)} className={selectCls}>
          <option value="">All Publish Statuses</option>
          <option value="3">Published</option>
          <option value="2">Submitted</option>
          <option value="1">Draft</option>
          <option value="5">Archived</option>
        </select>
        <select value={publicFilter} onChange={e => setPublicFilter(e.target.value)} className={selectCls}>
          <option value="">Public &amp; Internal</option>
          <option value="true">Public Only</option>
          <option value="false">Internal Only</option>
        </select>
        <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} className={selectCls}>
          <option value="">All Categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={scoreFilter} onChange={e => setScoreFilter(e.target.value)} className={selectCls}>
          <option value="">All Scores</option>
          <option value="low">Needs Review (&lt;5)</option>
          <option value="high">Good (≥5)</option>
        </select>
      </div>

      {isLoading && <p className="text-slate-500">Loading articles...</p>}
      {!isLoading && filtered.length === 0 && <p className="text-slate-500">No articles found.</p>}
      {filtered.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-100">
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Title</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Category</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Score</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Publish Status</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Visibility</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Modified</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(a => (
                <tr
                  key={a.id}
                  onClick={() => navigate(`/browser/${a.id}`)}
                  className="border-t border-slate-200 hover:bg-blue-50 cursor-pointer"
                >
                  <td className="px-4 py-3 text-sm text-blue-600 font-medium">{a.title}</td>
                  <td className="px-4 py-3 text-sm text-slate-500">{a.category_name ?? '—'}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`font-semibold ${a.heuristic_score < 5 ? 'text-red-500' : 'text-green-600'}`}>
                      {a.heuristic_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {a.tdx_status != null ? (
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${tdxStatusColor[a.tdx_status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {tdxStatusLabel[a.tdx_status] ?? `Status ${a.tdx_status}`}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${a.is_public ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
                      {a.is_public ? 'Public' : 'Internal'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {a.modified_at ? new Date(a.modified_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
