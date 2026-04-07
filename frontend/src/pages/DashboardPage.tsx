import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, CheckCircle, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import { useCarePlans } from '@/hooks/useOrders'
import { carePlanService } from '@/services/orderService'
import type { CarePlanListItem } from '@/types'
import { cn, formatDateTime, getStatusColor } from '@/utils/utils'

const PAGE_SIZE = 20

export function DashboardPage() {
  const [page, setPage] = useState(1)
  const [items, setItems] = useState<CarePlanListItem[]>([])
  const { data, isLoading, error } = useCarePlans(page, PAGE_SIZE)

  useEffect(() => {
    if (data) {
      setItems(data.results)
    }
  }, [data])

  const activeIds = useMemo(
    () => items.filter((item) => item.status === 'pending' || item.status === 'processing').map((item) => item.id),
    [items]
  )
  const activeIdsKey = useMemo(() => activeIds.join(','), [activeIds])

  useEffect(() => {
    if (activeIds.length === 0) {
      return
    }

    let cancelled = false

    const refreshStatuses = async () => {
      try {
        const response = await carePlanService.getStatuses(activeIds)
        if (cancelled) {
          return
        }

        const statusMap = new Map(response.results.map((item) => [item.id, item]))
        setItems((currentItems) =>
          currentItems.map((item) => {
            const next = statusMap.get(item.id)
            return next ? { ...item, status: next.status, error: next.error } : item
          })
        )
      } catch {
        // Keep the current list rendered if a polling request fails.
      }
    }

    refreshStatuses()
    const intervalId = window.setInterval(refreshStatuses, 3000)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [activeIdsKey])

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1
  const counts = useMemo(
    () => ({
      pending: items.filter((item) => item.status === 'pending').length,
      processing: items.filter((item) => item.status === 'processing').length,
      completed: items.filter((item) => item.status === 'completed').length,
      failed: items.filter((item) => item.status === 'failed').length,
    }),
    [items]
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">{(error as Error | undefined)?.message ?? 'Unable to load dashboard'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500">Polling every 3 seconds for pending and processing care plans on this page.</p>
        </div>
        <Link to="/" className="text-sm text-blue-600 hover:underline">
          New Order
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="Queued" value={counts.pending} tone="yellow" />
        <SummaryCard label="Generating" value={counts.processing} tone="blue" />
        <SummaryCard label="Ready" value={counts.completed} tone="green" />
        <SummaryCard label="Failed" value={counts.failed} tone="red" />
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patient</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Medication</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Diagnosis</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-4">
                  <div className="font-medium text-gray-900">{item.patient_name}</div>
                  <div className="text-sm text-gray-500">MRN: {item.mrn}</div>
                </td>
                <td className="px-4 py-4 text-sm text-gray-700">{item.medication}</td>
                <td className="px-4 py-4 text-sm text-gray-700">{item.diagnosis}</td>
                <td className="px-4 py-4 text-sm text-gray-500">{formatDateTime(item.created_at)}</td>
                <td className="px-4 py-4">
                  <span className={cn('inline-flex rounded-full px-2.5 py-1 text-xs font-medium', getStatusColor(item.status))}>
                    {item.status}
                  </span>
                  {item.error && <p className="mt-1 text-xs text-red-600">{item.error}</p>}
                </td>
                <td className="px-4 py-4 text-sm">
                  <Link to={`/care-plans/${item.id}`} className="text-blue-600 hover:underline">
                    View
                  </Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-gray-500">
                  No care plans yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Showing page {page} of {totalPages}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page === 1}
            className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </button>
          <button
            type="button"
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            disabled={page === totalPages}
            className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function SummaryCard({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'yellow' | 'blue' | 'green' | 'red'
}) {
  const icon = {
    yellow: <Loader2 className="h-4 w-4 text-yellow-600" />,
    blue: <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />,
    green: <CheckCircle className="h-4 w-4 text-green-600" />,
    red: <AlertCircle className="h-4 w-4 text-red-600" />,
  }[tone]

  const toneClass = {
    yellow: 'bg-yellow-50 border-yellow-200',
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    red: 'bg-red-50 border-red-200',
  }[tone]

  return (
    <div className={cn('rounded-lg border p-4', toneClass)}>
      <div className="flex items-center gap-2 text-sm text-gray-600">
        {icon}
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-gray-900">{value}</div>
    </div>
  )
}
