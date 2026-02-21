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
      <h1 className="mt-0 mb-6 text-2xl font-bold text-slate-800">Dashboard</h1>

      <div className="flex gap-4 mb-8 flex-wrap">
        <StatCard label="Pending Review" value={pending?.length ?? 0} />
        <StatCard label="Approved (not pushed)" value={approved?.length ?? 0} />
        <StatCard label="Total Scans" value={scans?.length ?? 0} />
      </div>

      <section className="mb-8">
        <h2 className="text-lg font-semibold text-slate-700 mb-2">Last Scan</h2>
        {lastScan ? (
          <p className="text-gray-700">
            Mode: <strong>{lastScan.mode}</strong> &nbsp;|&nbsp;
            Status:{' '}
            <strong className={lastScan.status === 'failed' ? 'text-red-600' : 'text-green-600'}>
              {lastScan.status}
            </strong> &nbsp;|&nbsp;
            Scanned: {lastScan.articles_scanned} &nbsp;|&nbsp;
            Flagged: {lastScan.articles_flagged} &nbsp;|&nbsp;
            At: {lastScan.started_at ? new Date(lastScan.started_at).toLocaleString() : '—'}
          </p>
        ) : (
          <p className="text-slate-500">No scans yet.</p>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-700 mb-3">Trigger Scan</h2>
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => trigger.mutate('heuristic')}
            disabled={trigger.isPending}
            className="px-5 py-2 bg-blue-500 text-white rounded-md text-sm font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Run Heuristic Scan
          </button>
          <button
            onClick={() => trigger.mutate('full_batch')}
            disabled={trigger.isPending}
            className="px-5 py-2 bg-violet-500 text-white rounded-md text-sm font-medium hover:bg-violet-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Run Full Batch Scan
          </button>
          {trigger.isPending && <span className="text-slate-500 text-sm">Starting scan...</span>}
          {trigger.isError && <span className="text-red-600 text-sm">Failed to start scan.</span>}
          {trigger.isSuccess && <span className="text-green-600 text-sm">Scan started.</span>}
        </div>
      </section>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg px-6 py-4 min-w-40 text-center shadow-sm">
      <div className="text-3xl font-bold text-slate-800">{value}</div>
      <div className="text-slate-500 text-sm mt-1">{label}</div>
    </div>
  )
}
