import { useState, useMemo } from 'react'

type SortDir = 'asc' | 'desc'

export function useSortableTable<T extends Record<string, unknown>>(data: T[]): {
  sorted: T[]
  sortKey: keyof T | null
  sortDir: SortDir
  toggleSort: (key: keyof T) => void
} {
  const [sortKey, setSortKey] = useState<keyof T | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  function toggleSort(key: keyof T) {
    if (key === sortKey) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => {
    if (sortKey === null) return data
    return [...data].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      // Nulls always sort to the bottom
      if (av == null && bv == null) return 0
      if (av == null) return 1
      if (bv == null) return -1

      let cmp: number
      if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv
      } else if (typeof av === 'boolean' && typeof bv === 'boolean') {
        cmp = (av ? 1 : 0) - (bv ? 1 : 0)
      } else {
        // Handles strings and ISO date strings (lexicographic order works for ISO)
        cmp = String(av).toLowerCase().localeCompare(String(bv).toLowerCase())
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortKey, sortDir])

  return { sorted, sortKey, sortDir, toggleSort }
}
