const ENV_VARS = [
  ['ANTHROPIC_API_KEY', 'Anthropic API key for Claude analysis'],
  ['TDX_BASE_URL', 'TeamDynamix instance base URL'],
  ['TDX_APP_ID', 'TDX Knowledge Base application ID'],
  ['TDX_BEID', 'TDX admin BEID for API authentication'],
  ['TDX_WEB_SERVICES_KEY', 'TDX admin Web Services Key'],
  ['SCAN_CRON', 'Cron expression for heuristic scan schedule (default: 0 2 * * *)'],
  ['HEURISTIC_THRESHOLD', 'Score below which articles are flagged (default: 5.0)'],
  ['CLAUDE_MODEL', 'Claude model to use (default: claude-sonnet-4-6)'],
]

export default function Settings() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Settings</h1>
      <p style={{ color: '#64748b', marginBottom: 20 }}>
        All credentials and configuration are managed via the <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>.env</code> file
        in the project root. Restart the backend after making changes.
      </p>
      <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f1f5f9' }}>
              <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, fontSize: 13, color: '#374151' }}>Variable</th>
              <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, fontSize: 13, color: '#374151' }}>Description</th>
            </tr>
          </thead>
          <tbody>
            {ENV_VARS.map(([key, desc]) => (
              <tr key={key} style={{ borderTop: '1px solid #e2e8f0' }}>
                <td style={{ padding: '10px 16px', fontFamily: 'monospace', fontSize: 13, fontWeight: 600, color: '#1e293b', whiteSpace: 'nowrap' }}>{key}</td>
                <td style={{ padding: '10px 16px', fontSize: 14, color: '#64748b' }}>{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
