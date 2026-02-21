import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listAudit } from '../api/audit'
import { listApproved, pushAll, pushOne } from '../api/push'

const statusColor: Record<string, string> = {
  success: 'text-green-600',
  pending: 'text-amber-600',
  failed: 'text-red-600',
}

export default function AuditLogView() {
  const queryClient = useQueryClient()

  const { data: approved, isLoading: loadingApproved } = useQuery({
    queryKey: ['approved'],
    queryFn: listApproved,
  })
  const { data: auditEntries, isLoading: loadingAudit } = useQuery({
    queryKey: ['audit'],
    queryFn: () => listAudit(100),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['approved'] })
    queryClient.invalidateQueries({ queryKey: ['audit'] })
    queryClient.invalidateQueries({ queryKey: ['queue'] })
  }

  const pushAllMutation = useMutation({ mutationFn: pushAll, onSuccess: invalidate })
  const pushOneMutation = useMutation({ mutationFn: pushOne, onSuccess: invalidate })

  const unpushed = (approved ?? []).filter(c => c.push_status !== 'success')

  return (
    <div>
      {/* Approved Changes */}
      <div className="flex items-center gap-4 mb-4">
        <h1 className="mt-0 mb-0 text-2xl font-bold text-slate-800">Approved Changes</h1>
        <button
          onClick={() => pushAllMutation.mutate()}
          disabled={pushAllMutation.isPending || unpushed.length === 0}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {pushAllMutation.isPending ? 'Pushing…' : `Push All Unpushed (${unpushed.length})`}
        </button>
        {pushAllMutation.isError && <span className="text-red-600 text-sm">Push failed.</span>}
        {pushAllMutation.isSuccess && <span className="text-green-600 text-sm">Push complete.</span>}
      </div>

      {loadingApproved && <p className="text-slate-500">Loading...</p>}
      {!loadingApproved && (approved?.length === 0) && (
        <p className="text-slate-500">No approved changes yet.</p>
      )}
      {(approved?.length ?? 0) > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm mb-10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-100">
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Article</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">TDX ID</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Approved At</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Error</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {approved?.map(c => (
                <tr key={c.id} className="border-t border-slate-200 hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-800">{c.article_title ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-500">{c.tdx_id ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {c.approved_at ? new Date(c.approved_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`font-semibold ${statusColor[c.push_status] ?? 'text-slate-500'}`}>
                      {c.push_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-red-600 max-w-xs break-words">
                    {c.push_error ?? ''}
                  </td>
                  <td className="px-4 py-3">
                    {c.push_status !== 'success' && (
                      <button
                        onClick={() => pushOneMutation.mutate(c.id)}
                        disabled={pushOneMutation.isPending}
                        className="px-3 py-1 bg-blue-500 text-white rounded text-xs font-medium hover:bg-blue-600 disabled:opacity-50"
                      >
                        Retry
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Push History */}
      <h2 className="text-xl font-bold text-slate-800 mb-3">Push History</h2>
      {loadingAudit && <p className="text-slate-500">Loading...</p>}
      {!loadingAudit && (auditEntries?.length === 0) && (
        <p className="text-slate-500">No successful pushes yet.</p>
      )}
      {(auditEntries?.length ?? 0) > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-100">
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">TDX ID</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Action</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Pushed At</th>
                <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Link</th>
              </tr>
            </thead>
            <tbody>
              {auditEntries?.map(e => (
                <tr key={e.id} className="border-t border-slate-200 hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-800">{e.tdx_id}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{e.action}</td>
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {e.pushed_at ? new Date(e.pushed_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <a href={e.tdx_url} target="_blank" rel="noreferrer"
                      className="text-blue-500 hover:text-blue-700">
                      View ↗
                    </a>
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
