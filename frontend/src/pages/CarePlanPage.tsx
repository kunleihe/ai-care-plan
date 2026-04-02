import { useParams, Link } from 'react-router-dom'
import { Loader2, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { useCarePlanStatus } from '@/hooks/useOrders'
import { cn, getStatusColor } from '@/utils/utils'

export function CarePlanPage() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, error } = useCarePlanStatus(id!)

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
        <p className="text-red-700">{error?.message ?? 'Care plan not found'}</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Care Plan</h1>
        <span className={cn('px-3 py-1 rounded-full text-xs font-semibold uppercase', getStatusColor(data.status))}>
          {data.status}
        </span>
      </div>

      {/* Patient / Order info */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-5">
          <h2 className="text-sm font-semibold text-blue-700 uppercase tracking-wide mb-3">Patient</h2>
          <dl className="space-y-2 text-sm">
            <div><dt className="text-gray-500">Name</dt><dd className="font-medium">{data.patient.first_name} {data.patient.last_name}</dd></div>
            <div><dt className="text-gray-500">MRN</dt><dd className="font-mono">{data.patient.mrn}</dd></div>
          </dl>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <h2 className="text-sm font-semibold text-blue-700 uppercase tracking-wide mb-3">Order</h2>
          <dl className="space-y-2 text-sm">
            <div><dt className="text-gray-500">Medication</dt><dd className="font-medium">{data.order.medication}</dd></div>
            <div><dt className="text-gray-500">Diagnosis</dt><dd className="font-mono">{data.order.diagnosis}</dd></div>
            <div><dt className="text-gray-500">Provider</dt><dd>{data.order.referring_provider}</dd></div>
          </dl>
        </div>
      </div>

      {/* Status / Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {(data.status === 'pending' || data.status === 'processing') && (
          <div className="flex items-center gap-3 text-blue-600">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm">
              {data.status === 'pending' ? 'Waiting in queue...' : 'Generating care plan...'}
            </span>
            <span className="text-xs text-gray-400">(auto-refreshing every 3s)</span>
          </div>
        )}

        {data.status === 'completed' && data.content && (
          <>
            <div className="flex items-center gap-2 text-green-600 mb-4">
              <CheckCircle className="h-5 w-5" />
              <span className="text-sm font-medium">Care plan ready</span>
            </div>
            <pre className="bg-gray-50 rounded-lg p-4 text-sm whitespace-pre-wrap font-mono overflow-auto max-h-[600px]">
              {data.content}
            </pre>
          </>
        )}

        {data.status === 'failed' && (
          <div className="flex items-center gap-2 text-red-600">
            <AlertCircle className="h-5 w-5" />
            <span className="text-sm">Generation failed. Please try again.</span>
          </div>
        )}

        {data.status === 'pending' && (
          <div className="flex items-center gap-2 text-yellow-600 mt-3">
            <Clock className="h-4 w-4" />
            <span className="text-xs text-gray-500">Care Plan ID: {data.id}</span>
          </div>
        )}
      </div>

      <p className="mt-6">
        <Link to="/" className="text-blue-600 text-sm hover:underline">
          ← Generate another care plan
        </Link>
      </p>
    </div>
  )
}
