import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactDiffViewer from 'react-diff-viewer-continued'
import { getArticleAnalysis } from '../api/articles'
import { approveItem, rejectItem, skipItem } from '../api/queue'

const tierBadge: Record<string, string> = {
  auto: 'bg-green-600',
  confirm: 'bg-amber-500',
  admin: 'bg-red-600',
}

const scoreColor = (v: number) => (v < 6 ? 'text-red-500' : 'text-green-600')

const DIMS = [
  { key: 'score_clarity', label: 'Clarity' },
  { key: 'score_completeness', label: 'Completeness' },
  { key: 'score_findability', label: 'Findability' },
  { key: 'score_redundancy', label: 'Redundancy' },
  { key: 'score_accuracy', label: 'Accuracy' },
] as const

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>()
  const articleId = Number(id)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['article-detail', articleId],
    queryFn: () => getArticleAnalysis(articleId),
  })

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['article-detail', articleId] })
    qc.invalidateQueries({ queryKey: ['queue'] })
  }

  const approve = useMutation({ mutationFn: (qid: number) => approveItem(qid), onSuccess: invalidate })
  const reject = useMutation({
    mutationFn: ({ qid, note }: { qid: number; note: string }) => rejectItem(qid, note),
    onSuccess: invalidate,
  })
  const skip = useMutation({ mutationFn: (qid: number) => skipItem(qid), onSuccess: invalidate })

  if (isLoading) return <p className="text-slate-500">Loading...</p>
  if (error || !data) return <p className="text-red-500">Failed to load article.</p>

  const { article, analysis, queue_item } = data
  const isPending = queue_item?.status === 'pending'

  return (
    <div>
      {/* Back */}
      <button
        onClick={() => navigate('/browser')}
        className="text-sm text-blue-500 hover:text-blue-700 mb-4 flex items-center gap-1"
      >
        ← Back to Article Browser
      </button>

      {/* Header */}
      <div className="flex justify-between items-start mb-1">
        <h1 className="mt-0 text-2xl font-bold text-slate-800 mr-4">{article.title}</h1>
        {analysis && (
          <span className={`shrink-0 ${tierBadge[analysis.approval_tier] ?? 'bg-slate-500'} text-white px-3 py-1 rounded-full text-xs font-semibold`}>
            {analysis.approval_tier.toUpperCase()}
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500 mb-6">
        <span>{article.category_name ?? 'Uncategorized'}</span>
        <span>·</span>
        <span className={`font-semibold ${scoreColor(article.heuristic_score)}`}>
          Heuristic: {article.heuristic_score.toFixed(1)}
        </span>
        <span>·</span>
        <span>{article.view_count ?? 0} views</span>
        {article.modified_at && (
          <>
            <span>·</span>
            <span>Modified {new Date(article.modified_at).toLocaleDateString()}</span>
          </>
        )}
        {article.tdx_url && (
          <>
            <span>·</span>
            <a href={article.tdx_url} target="_blank" rel="noreferrer" className="text-blue-500 hover:text-blue-700">
              View in TDX ↗
            </a>
          </>
        )}
      </div>

      {/* No analysis yet */}
      {!analysis && (
        <div className="bg-white border border-slate-200 rounded-lg p-6 text-slate-500">
          No analysis available yet. Run a scan to analyze this article.
        </div>
      )}

      {analysis && (
        <>
          {/* Score breakdown */}
          <div className="bg-white border border-slate-200 rounded-lg p-6 mb-6 shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-base font-semibold text-slate-700 m-0">Quality Scores</h2>
              {analysis.analyzed_at && (
                <span className="text-xs text-slate-400">
                  Analyzed {new Date(analysis.analyzed_at).toLocaleString()}
                </span>
              )}
            </div>

            <div className="grid grid-cols-3 sm:grid-cols-6 gap-4 mb-5">
              {/* Overall */}
              <div className="text-center col-span-1">
                <div className={`text-3xl font-bold ${scoreColor(analysis.overall_score)}`}>
                  {analysis.overall_score.toFixed(1)}
                </div>
                <div className="text-xs text-slate-500 mt-1 font-semibold uppercase tracking-wide">Overall</div>
              </div>
              {/* Dimensions */}
              {DIMS.map(({ key, label }) => (
                <div key={key} className="text-center">
                  <div className={`text-xl font-bold ${scoreColor(analysis[key])}`}>
                    {analysis[key].toFixed(1)}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">{label}</div>
                </div>
              ))}
            </div>

            <p className="text-gray-700 text-sm mb-0">
              <strong>Issues:</strong> {analysis.issue_summary}
            </p>

            {analysis.defects.length > 0 && (
              <ul className="mt-2 text-slate-500 text-sm pl-5 space-y-1">
                {analysis.defects.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Queue status + actions */}
          {queue_item && (
            <div className="flex items-center gap-4 mb-4">
              <span className="text-sm text-slate-500">
                Queue status:{' '}
                <strong className={
                  queue_item.status === 'approved' ? 'text-green-600' :
                  queue_item.status === 'rejected' ? 'text-red-600' :
                  queue_item.status === 'skipped' ? 'text-slate-400' :
                  'text-amber-600'
                }>
                  {queue_item.status}
                </strong>
              </span>
              {queue_item.reviewer_note && (
                <span className="text-sm text-slate-400 italic">"{queue_item.reviewer_note}"</span>
              )}
              {isPending && (
                <div className="flex gap-2">
                  <button
                    onClick={() => approve.mutate(queue_item.id)}
                    disabled={approve.isPending}
                    className="px-4 py-1.5 bg-green-600 text-white rounded text-sm font-semibold hover:bg-green-700 disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => {
                      const note = window.prompt('Rejection reason (optional):') ?? ''
                      reject.mutate({ qid: queue_item.id, note })
                    }}
                    disabled={reject.isPending}
                    className="px-4 py-1.5 bg-red-600 text-white rounded text-sm font-semibold hover:bg-red-700 disabled:opacity-50"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => skip.mutate(queue_item.id)}
                    disabled={skip.isPending}
                    className="px-4 py-1.5 bg-slate-500 text-white rounded text-sm font-semibold hover:bg-slate-600 disabled:opacity-50"
                  >
                    Skip
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Diff */}
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
              <h2 className="text-sm font-semibold text-slate-700 m-0">Proposed Changes</h2>
            </div>
            <ReactDiffViewer
              oldValue={article.body}
              newValue={analysis.proposed_body}
              splitView={true}
              leftTitle="Current"
              rightTitle="Proposed"
            />
          </div>
        </>
      )}
    </div>
  )
}
