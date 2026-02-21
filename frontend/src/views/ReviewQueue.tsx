import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listQueue, approveItem, rejectItem, skipItem } from '../api/queue'
import DiffReview from '../components/DiffReview'

export default function ReviewQueue() {
  const qc = useQueryClient()
  const { data: items, isLoading } = useQuery({
    queryKey: ['queue', 'pending'],
    queryFn: () => listQueue('pending'),
  })

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['queue'] })
    qc.invalidateQueries({ queryKey: ['scans'] })
  }

  const approve = useMutation({
    mutationFn: ({ id, body }: { id: number; body?: string }) => approveItem(id, body),
    onSuccess: invalidate,
  })
  const reject = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) => rejectItem(id, note),
    onSuccess: invalidate,
  })
  const skip = useMutation({
    mutationFn: (id: number) => skipItem(id),
    onSuccess: invalidate,
  })

  if (isLoading) return <p>Loading queue...</p>

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>
        Review Queue
        <span style={{ fontSize: 15, fontWeight: 400, color: '#64748b', marginLeft: 8 }}>
          ({items?.length ?? 0} pending)
        </span>
      </h1>
      {items?.length === 0 && <p style={{ color: '#64748b' }}>Queue is empty — run a scan to populate it.</p>}
      {items?.map(item => (
        <DiffReview
          key={item.id}
          item={item}
          onApprove={(id, body) => approve.mutate({ id, body })}
          onReject={(id, note) => reject.mutate({ id, note })}
          onSkip={id => skip.mutate(id)}
        />
      ))}
    </div>
  )
}
