import { useState } from 'react'
import ReactDiffViewer from 'react-diff-viewer-continued'
import RichTextEditor from './RichTextEditor'
import type { QueueItem } from '../api/types'

interface Props {
  item: QueueItem
  onApprove: (id: number, editedBody?: string) => void
  onReject: (id: number, note: string) => void
  onSkip: (id: number) => void
}

const tierBadge: Record<string, string> = {
  auto: 'bg-green-600',
  confirm: 'bg-amber-500',
  admin: 'bg-red-600',
}

export default function DiffReview({ item, onApprove, onReject, onSkip }: Props) {
  const [editMode, setEditMode] = useState(false)
  const [editedBody, setEditedBody] = useState(item.analysis.proposed_body)

  const defects: string[] = item.analysis.defects ?? []
  const scores: Record<string, number> = {
    clarity: item.analysis.score_clarity,
    completeness: item.analysis.score_completeness,
    findability: item.analysis.score_findability,
    redundancy: item.analysis.score_redundancy,
    accuracy: item.analysis.score_accuracy,
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 mb-6 shadow-sm">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h2 className="text-lg font-bold text-slate-800 m-0 mb-1">
            {item.article.title}
            {item.article.tdx_url && (
              <a
                href={item.article.tdx_url}
                target="_blank"
                rel="noreferrer"
                className="ml-3 text-sm font-normal text-blue-500 hover:text-blue-700 no-underline"
              >
                View in TDX ↗
              </a>
            )}
          </h2>
          <span className="text-sm text-slate-500">
            {item.article.category_name ?? 'Uncategorized'} &nbsp;|&nbsp;
            Overall: <strong className="text-slate-700">{item.analysis.overall_score.toFixed(1)}</strong>
          </span>
        </div>
        <span className={`${tierBadge[item.analysis.approval_tier] ?? 'bg-slate-500'} text-white px-3 py-1 rounded-full text-xs font-semibold`}>
          {item.analysis.approval_tier.toUpperCase()}
        </span>
      </div>

      <div className="flex gap-5 mb-3 flex-wrap">
        {(['clarity', 'completeness', 'findability', 'redundancy', 'accuracy'] as const).map(dim => (
          <div key={dim} className="text-center min-w-[60px]">
            <div className={`text-xl font-bold ${scores[dim] < 6 ? 'text-red-500' : 'text-green-600'}`}>
              {scores[dim].toFixed(1)}
            </div>
            <div className="text-xs text-slate-500 capitalize">{dim}</div>
          </div>
        ))}
      </div>

      <p className="text-gray-700 mb-2"><strong>Issues:</strong> {item.analysis.issue_summary}</p>
      {defects.length > 0 && (
        <ul className="text-slate-500 text-sm mb-4 pl-5 space-y-1">
          {defects.map((d, i) => <li key={`defect-${i}-${d.slice(0, 20)}`}>{d}</li>)}
        </ul>
      )}

      {/* Diff / Edit toggle */}
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => setEditMode(false)}
          className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${
            !editMode
              ? 'bg-slate-700 text-white border-slate-700'
              : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
          }`}
        >
          View Diff
        </button>
        <button
          onClick={() => setEditMode(true)}
          className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${
            editMode
              ? 'bg-slate-700 text-white border-slate-700'
              : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
          }`}
        >
          Edit Proposed
        </button>
        {editMode && editedBody !== item.analysis.proposed_body && (
          <span className="text-xs text-amber-600 font-medium">Edited</span>
        )}
      </div>

      {editMode ? (
        <RichTextEditor
          initialContent={item.analysis.proposed_body}
          onChange={setEditedBody}
        />
      ) : (
        <ReactDiffViewer
          oldValue={item.article.body}
          newValue={editedBody}
          splitView={true}
          leftTitle="Current"
          rightTitle={editedBody !== item.analysis.proposed_body ? 'Proposed (edited)' : 'Proposed'}
        />
      )}

      <div className="flex gap-3 mt-4">
        <button
          onClick={() => onApprove(item.id, editedBody !== item.analysis.proposed_body ? editedBody : undefined)}
          className="px-5 py-2 bg-green-600 text-white rounded-md font-semibold text-sm hover:bg-green-700"
        >
          {editedBody !== item.analysis.proposed_body ? 'Approve (edited)' : 'Approve'}
        </button>
        <button
          onClick={() => {
            const note = window.prompt('Rejection reason (optional):') ?? ''
            onReject(item.id, note)
          }}
          className="px-5 py-2 bg-red-600 text-white rounded-md font-semibold text-sm hover:bg-red-700"
        >
          Reject
        </button>
        <button
          onClick={() => onSkip(item.id)}
          className="px-5 py-2 bg-slate-500 text-white rounded-md font-semibold text-sm hover:bg-slate-600"
        >
          Skip
        </button>
      </div>
    </div>
  )
}
