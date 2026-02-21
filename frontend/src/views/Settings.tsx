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

export default function Settings() {
  return (
    <div>
      <h1 className="mt-0 mb-2 text-2xl font-bold text-slate-800">Settings</h1>
      <p className="text-slate-500 mb-5">
        All credentials and configuration are managed via the{' '}
        <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono">.env</code>{' '}
        file in the project root. Restart the backend after making changes.
      </p>
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
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
    </div>
  )
}
