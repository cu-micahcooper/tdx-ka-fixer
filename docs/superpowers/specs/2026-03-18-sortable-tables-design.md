# Sortable Tables — Design Spec

**Date:** 2026-03-18
**Status:** Approved

## Goal

Add click-to-sort column headers to all table-based list views. First click sorts ascending, second click sorts descending, then toggles between the two indefinitely. An up/down indicator (↑/↓) appears next to the active sort column. The Review Queue (card-based, not a table) is excluded.

## Scope

Three tables:
- **Article Browser** (`ArticleBrowser.tsx`) — all 6 columns sortable: Title, Category, Score, Publish Status, Visibility, Modified
- **Approved Changes** (`AuditLogView.tsx`) — 4 columns: Article, TDX ID, Approved At, Status
- **Push History** (`AuditLogView.tsx`) — 3 columns: TDX ID, Action, Pushed At

## Approach

A `useSortableTable` hook encapsulates sort state and comparator logic. Each table calls the hook once and gets back sorted data + the current sort state for rendering indicators. No generic table component — each view keeps its own cell rendering (badges, colored scores, links, etc.).

## Hook Design

**File:** `frontend/src/hooks/useSortableTable.ts`

```ts
export function useSortableTable<T extends Record<string, unknown>>(
  data: T[]
): {
  sorted: T[]
  sortKey: keyof T | null
  sortDir: 'asc' | 'desc'
  toggleSort: (key: keyof T) => void
}
```

**State:** `{ key: keyof T | null, dir: 'asc' | 'desc' }`, initialized to `{ key: null, dir: 'asc' }`.

**`toggleSort(key)` logic:**
- If `key !== current key` → set key, set dir to `'asc'`
- If `key === current key` → flip dir (`'asc'` ↔ `'desc'`)

**Sorting:** `[...data].sort(comparator)`. When `key === null`, returns data unchanged (original server order preserved).

**Comparator:** Generic — handles strings (case-insensitive), numbers, booleans, and ISO date strings. Null/undefined values always sort to the bottom regardless of direction.

## Header Rendering

Each sortable `<th>`:
- `cursor-pointer select-none` classes
- `onClick={() => toggleSort(key)}`
- Label followed by sort indicator: `↑` when active+asc, `↓` when active+desc, nothing when inactive
- Subtle hover: `hover:bg-slate-200` (current header bg is `bg-slate-100`)

Example:
```tsx
<th onClick={() => toggleSort('title')} className="... cursor-pointer select-none hover:bg-slate-200">
  Title {sortKey === 'title' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
</th>
```

## Files Changed

| File | Change |
|---|---|
| `frontend/src/hooks/useSortableTable.ts` | New hook |
| `frontend/src/views/ArticleBrowser.tsx` | Add sorting to all 6 columns |
| `frontend/src/views/AuditLogView.tsx` | Add sorting to Approved Changes + Push History tables |

## What Does Not Change

- No backend changes — all sorting is client-side on already-loaded data
- Cell rendering (badges, colors, links) unchanged
- Filter/search logic in ArticleBrowser unchanged — sorting is applied after filtering
- ReviewQueue unchanged
