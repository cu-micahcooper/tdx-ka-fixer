// frontend/src/views/Settings.tsx
import { useState, useEffect } from 'react'
import { getSettings, patchSettings, type AppSettings } from '../api/settings'

const ENV_VARS = [
  ['ANTHROPIC_API_KEY', 'Anthropic API key for Claude analysis'],
  ['TDX_BASE_URL', 'TeamDynamix instance base URL'],
  ['TDX_APP_ID', 'TDX Knowledge Base application ID'],
  ['TDX_USERNAME', 'TDX username for API authentication'],
  ['TDX_PASSWORD', 'TDX password for API authentication'],
  ['SCAN_CRON', 'Cron expression for heuristic scan schedule (default: 0 2 * * *)'],
  ['HEURISTIC_THRESHOLD', 'Score below which articles are flagged (default: 5.0)'],
  ['CLAUDE_MODEL', 'Claude model to use (default: claude-sonnet-4-6)'],
]

type SaveStatus = 'idle' | 'loading' | 'saving' | 'saved' | 'error'

export default function Settings() {
  const [internal, setInternal] = useState('')
  const [pub, setPub] = useState('')
  const [status, setStatus] = useState<SaveStatus>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    getSettings()
      .then((data) => {
        setInternal(data.internal_directive)
        setPub(data.public_directive)
        setStatus('idle')
      })
      .catch(() => {
        setStatus('error')
        setErrorMsg('Failed to load settings.')
      })
  }, [])

  async function handleSave() {
    setStatus('saving')
    setErrorMsg('')
    try {
      const updated = await patchSettings({
        internal_directive: internal,
        public_directive: pub,
      })
      setInternal(updated.internal_directive)
      setPub(updated.public_directive)
      setStatus('saved')
      setTimeout(() => setStatus('idle'), 2000)
    } catch {
      setStatus('error')
      setErrorMsg('Failed to save settings.')
    }
  }

  const isBusy = status === 'loading' || status === 'saving'

  return (
    <div>
      <h1 className="mt-0 mb-2 text-2xl font-bold text-slate-800">Settings</h1>

      {/* Env vars reference table — unchanged */}
      <p className="text-slate-500 mb-5">
        All credentials and configuration are managed via the{' '}
        <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono">.env</code>{' '}
        file in the project root. Restart the backend after making changes.
      </p>
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden mb-8">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-slate-100">
              <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Variable</th>
              <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Description</th>
            </tr>
          </thead>
          <tbody>
            {ENV_VARS.map(([key, desc]) => (
              <tr key={key} className="border-t border-slate-200">
                <td className="px-4 py-3 font-mono text-sm font-semibold text-slate-800 whitespace-nowrap">{key}</td>
                <td className="px-4 py-3 text-sm text-slate-500">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* AI Directives — interactive */}
      <h2 className="text-lg font-semibold text-slate-800 mb-1">AI Directives</h2>
      <p className="text-slate-500 text-sm mb-5">
        These directives are injected into the Claude analysis prompt as institutional context.
        Changes take effect on the next scan. Use separate directives to tailor tone and detail
        for internal staff vs. public-facing audiences.
      </p>

      {status === 'loading' && (
        <p className="text-slate-400 text-sm">Loading…</p>
      )}

      {status !== 'loading' && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">
              Internal Articles{' '}
              <span className="font-normal text-slate-400">(non-public)</span>
            </label>
            <textarea
              className="w-full h-52 px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono text-slate-800 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={internal}
              onChange={(e) => { setInternal(e.target.value); setStatus('idle') }}
              disabled={isBusy}
              placeholder="Describe the institutional context for internal articles…"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">
              Public Articles
            </label>
            <textarea
              className="w-full h-52 px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono text-slate-800 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={pub}
              onChange={(e) => { setPub(e.target.value); setStatus('idle') }}
              disabled={isBusy}
              placeholder="Describe the institutional context for public-facing articles…"
            />
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={handleSave}
              disabled={isBusy}
              className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {status === 'saving' ? 'Saving…' : 'Save Directives'}
            </button>
            {status === 'saved' && (
              <span className="text-green-600 text-sm font-medium">Saved</span>
            )}
            {status === 'error' && (
              <span className="text-red-600 text-sm">{errorMsg}</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
