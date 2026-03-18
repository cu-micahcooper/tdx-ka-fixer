import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listScans, triggerScan } from '../api/scans'
import { listQueue } from '../api/queue'
import { getStats } from '../api/stats'
import type { CategoryStat } from '../api/stats'

const tdxStatusColor: Record<number, string> = {
  1: 'bg-slate-100 text-slate-600',
  2: 'bg-amber-100 text-amber-700',
  3: 'bg-green-100 text-green-700',
  5: 'bg-red-100 text-red-700',
}

function scoreColor(score: number | null) {
  if (score === null) return 'text-slate-400'
  return score < 5 ? 'text-red-500' : score < 7 ? 'text-amber-500' : 'text-green-600'
}

function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-slate-400 text-xs">—</span>
  const pct = Math.round((score / 10) * 100)
  const color = score < 5 ? 'bg-red-400' : score < 7 ? 'bg-amber-400' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-slate-100 rounded-full h-1.5 shrink-0">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-semibold ${scoreColor(score)}`}>{score.toFixed(1)}</span>
    </div>
  )
}

export default function Dashboard() {
  const qc = useQueryClient()
  const { data: scans } = useQuery({
    queryKey: ['scans'],
    queryFn: listScans,
    refetchInterval: (query) => query.state.data?.[0]?.status === 'running' ? 3000 : false,
  })
  const { data: pending } = useQuery({ queryKey: ['queue', 'pending'], queryFn: () => listQueue('pending') })
  const { data: approved } = useQuery({ queryKey: ['queue', 'approved'], queryFn: () => listQueue('approved') })
  const { data: stats } = useQuery({ queryKey: ['stats'], queryFn: getStats })

  const trigger = useMutation({
    mutationFn: triggerScan,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scans'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const navigate = useNavigate()
  const lastScan = scans?.[0]

  return (
    <div>
      <h1 className="mt-0 mb-6 text-2xl font-bold text-slate-800">Dashboard</h1>

      {/* Top stat cards */}
      <div className="flex gap-4 mb-8 flex-wrap">
        <StatCard label="Total Articles" value={stats?.total_articles ?? 0} onClick={() => navigate('/browser')} />
        <StatCard label="Pending Review" value={pending?.length ?? 0} color="text-amber-600" onClick={() => navigate('/queue')} />
        <StatCard label="Approved (not pushed)" value={approved?.length ?? 0} color="text-green-600" onClick={() => navigate('/audit')} />
        <StatCard label="Needs Review" value={stats?.needs_review_count ?? 0} color="text-red-500" onClick={() => navigate('/browser?score=low')} />
        {stats?.avg_heuristic_score != null && (
          <StatCard label="Avg Quality Score" value={stats.avg_heuristic_score} decimals={1} />
        )}
      </div>

      {/* Publish status + Visibility side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* By Publish Status */}
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 bg-slate-50">
            <h2 className="text-sm font-semibold text-slate-700 m-0">By Publish Status</h2>
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-xs text-slate-500 border-b border-slate-100">
                <th className="px-4 py-2 text-left font-medium">Status</th>
                <th className="px-4 py-2 text-right font-medium">Articles</th>
                <th className="px-4 py-2 text-right font-medium">Needs Review</th>
                <th className="px-4 py-2 text-left font-medium pl-6">Avg Score</th>
              </tr>
            </thead>
            <tbody>
              {(stats?.by_publish_status ?? []).map(s => (
                <tr key={s.tdx_status ?? 'null'} onClick={() => s.tdx_status != null && navigate(`/browser?tdx_status=${s.tdx_status}`)} className={`border-t border-slate-100 hover:bg-blue-50 ${s.tdx_status != null ? 'cursor-pointer' : ''}`}>
                  <td className="px-4 py-2.5">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${s.tdx_status != null ? (tdxStatusColor[s.tdx_status] ?? 'bg-slate-100 text-slate-600') : 'bg-slate-100 text-slate-400'}`}>
                      {s.label}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right text-slate-700 font-medium">{s.count.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-sm text-right">
                    <span className={s.needs_review > 0 ? 'text-red-500 font-semibold' : 'text-slate-400'}>
                      {s.needs_review}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 pl-6"><ScoreBar score={s.avg_score} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* By Visibility */}
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 bg-slate-50">
            <h2 className="text-sm font-semibold text-slate-700 m-0">By Visibility</h2>
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-xs text-slate-500 border-b border-slate-100">
                <th className="px-4 py-2 text-left font-medium">Visibility</th>
                <th className="px-4 py-2 text-right font-medium">Articles</th>
                <th className="px-4 py-2 text-right font-medium">Needs Review</th>
                <th className="px-4 py-2 text-left font-medium pl-6">Avg Score</th>
              </tr>
            </thead>
            <tbody>
              {(stats?.by_visibility ?? []).map(v => (
                <tr key={String(v.is_public)} onClick={() => navigate(`/browser?is_public=${v.is_public}`)} className="border-t border-slate-100 hover:bg-blue-50 cursor-pointer">
                  <td className="px-4 py-2.5">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${v.is_public ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
                      {v.label}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right text-slate-700 font-medium">{v.count.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-sm text-right">
                    <span className={v.needs_review > 0 ? 'text-red-500 font-semibold' : 'text-slate-400'}>
                      {v.needs_review}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 pl-6"><ScoreBar score={v.avg_score} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* By Category */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden mb-8">
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700 m-0">By Category</h2>
          <span className="text-xs text-slate-400">{stats?.by_category.length ?? 0} categories</span>
        </div>
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 bg-slate-50 z-10">
              <tr className="text-xs text-slate-500 border-b border-slate-100">
                <th className="px-4 py-2 text-left font-medium">Category</th>
                <th className="px-4 py-2 text-right font-medium">Articles</th>
                <th className="px-4 py-2 text-right font-medium">Needs Review</th>
                <th className="px-4 py-2 text-left font-medium pl-6">Avg Score</th>
                <th className="px-4 py-2 text-right font-medium">% Needs Review</th>
              </tr>
            </thead>
            <tbody>
              {(stats?.by_category ?? []).map((c: CategoryStat) => {
                const pctReview = c.count > 0 ? Math.round((c.needs_review / c.count) * 100) : 0
                return (
                  <tr key={c.category_name} onClick={() => navigate(`/browser?category=${encodeURIComponent(c.category_name)}`)} className="border-t border-slate-100 hover:bg-blue-50 cursor-pointer">
                    <td className="px-4 py-2 text-sm text-slate-700">{c.category_name}</td>
                    <td className="px-4 py-2 text-sm text-right text-slate-600">{c.count}</td>
                    <td className="px-4 py-2 text-sm text-right">
                      <span className={c.needs_review > 0 ? 'text-red-500 font-semibold' : 'text-slate-400'}>
                        {c.needs_review}
                      </span>
                    </td>
                    <td className="px-4 py-2 pl-6"><ScoreBar score={c.avg_score} /></td>
                    <td className="px-4 py-2 text-xs text-right">
                      <span className={pctReview > 20 ? 'text-red-500 font-semibold' : pctReview > 5 ? 'text-amber-500' : 'text-slate-400'}>
                        {pctReview > 0 ? `${pctReview}%` : '—'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Last Scan + Trigger */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Last Scan</h2>
          {lastScan ? (
            <>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                <dt className="text-slate-500">Mode</dt>
                <dd className="text-slate-700 font-medium">{lastScan.mode}</dd>
                <dt className="text-slate-500">Status</dt>
                <dd className={lastScan.status === 'failed' ? 'text-red-600 font-semibold' : lastScan.status === 'running' ? 'text-blue-600 font-semibold' : 'text-green-600 font-semibold'}>{lastScan.status}</dd>
                <dt className="text-slate-500">Scanned</dt>
                <dd className="text-slate-700">{lastScan.articles_scanned}</dd>
                <dt className="text-slate-500">Flagged</dt>
                <dd className="text-slate-700">{lastScan.articles_flagged}</dd>
                <dt className="text-slate-500">Started</dt>
                <dd className="text-slate-700">{lastScan.started_at ? new Date(lastScan.started_at).toLocaleString() : '—'}</dd>
              </dl>
              {lastScan.status === 'running' && (
                <ScanProgress scanned={lastScan.articles_scanned} total={lastScan.articles_total} />
              )}
              {lastScan.status === 'failed' && (
                <ScanErrorDetail error={lastScan.error} />
              )}
            </>
          ) : (
            <p className="text-slate-500 text-sm">No scans yet.</p>
          )}
        </section>

        <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Trigger Scan</h2>
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
    </div>
  )
}

function classifyError(error: string | null): { label: string; hint: string } | null {
  if (!error) return null
  const e = error.toLowerCase()
  if (e.includes('json') || e.includes("delimiter") || e.includes("parse") || e.includes("expecting")) {
    return {
      label: 'Claude returned malformed JSON',
      hint: 'Claude\'s response contained invalid JSON (often unescaped characters in a proposed HTML rewrite). This is a transient AI output issue. Re-running the scan usually succeeds. If it keeps failing on the same article, check the article body for unusual characters.',
    }
  }
  if (e.includes('401') || e.includes('auth') || e.includes('unauthorized')) {
    return {
      label: 'TDX authentication failed',
      hint: 'The TDX credentials in .env are invalid or expired. Check TDX_USERNAME and TDX_PASSWORD (or BEID/WebServicesKey) and restart the backend.',
    }
  }
  if (e.includes('errno 60') || e.includes('timed out') || e.includes('timeout')) {
    return {
      label: 'TDX request timed out',
      hint: 'TDX is rate-limiting or unreachable. This happens when requests are made faster than the 5-second interval, or when VPN/network access to TDX is unavailable. Ensure you\'re on the Cedarville network or VPN, then retry.',
    }
  }
  if (e.includes('ratelimit') || e.includes('rate limit') || e.includes('429')) {
    return {
      label: 'Anthropic API rate limit hit',
      hint: 'The Anthropic API rate limit was exceeded. Wait a few minutes and retry. Full batch scans call Claude once per article, which can exhaust the token-per-minute limit on lower-tier API plans.',
    }
  }
  if (e.includes('api_key') || e.includes('anthropic') || e.includes('authentication_error')) {
    return {
      label: 'Anthropic API key error',
      hint: 'Check ANTHROPIC_API_KEY in .env — the key may be missing, invalid, or revoked.',
    }
  }
  if (e.includes('connection') || e.includes('network') || e.includes('errno 111') || e.includes('connect')) {
    return {
      label: 'Network connection error',
      hint: 'Could not reach TDX or the Anthropic API. Check your network/VPN connection and verify TDX_BASE_URL in .env.',
    }
  }
  return {
    label: 'Unexpected error',
    hint: 'An unexpected error occurred. Check the backend terminal output for a full traceback.',
  }
}

function ScanProgress({ scanned, total }: { scanned: number; total: number }) {
  const pct = total > 0 ? Math.round((scanned / total) * 100) : 0
  const label = total > 0 ? `${scanned} / ${total} articles (${pct}%)` : `${scanned} articles…`
  return (
    <div className="mt-4">
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>Scanning…</span>
        <span>{label}</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-500"
          style={{ width: total > 0 ? `${pct}%` : '100%', opacity: total > 0 ? 1 : 0.4 }}
        />
      </div>
    </div>
  )
}

function ScanErrorDetail({ error }: { error: string | null }) {
  const info = classifyError(error)
  return (
    <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm">
      <p className="font-semibold text-red-700 mb-1">{info?.label ?? 'Scan failed'}</p>
      {error && (
        <p className="font-mono text-xs text-red-600 bg-red-100 rounded px-2 py-1 mb-2 break-all">{error}</p>
      )}
      {info?.hint && (
        <p className="text-red-700 text-xs leading-relaxed">{info.hint}</p>
      )}
    </div>
  )
}

function StatCard({
  label, value, color = 'text-slate-800', decimals = 0, onClick,
}: {
  label: string
  value: number
  color?: string
  decimals?: number
  onClick?: () => void
}) {
  return (
    <div
      onClick={onClick}
      className={`bg-white border border-slate-200 rounded-lg px-6 py-4 min-w-40 text-center shadow-sm transition-colors ${onClick ? 'cursor-pointer hover:bg-blue-50 hover:border-blue-200' : ''}`}
    >
      <div className={`text-3xl font-bold ${color}`}>
        {decimals > 0 ? value.toFixed(decimals) : value.toLocaleString()}
      </div>
      <div className="text-slate-500 text-sm mt-1">{label}</div>
    </div>
  )
}
