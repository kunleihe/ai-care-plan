import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useCreateOrder } from '@/hooks/useOrders'
import { FormField } from '@/components/forms/FormField'
import { Button } from '@/components/ui/Button'
import { AppError } from '@/services/api'
import { orderSchema, type OrderFormData } from '@/utils/validators'
import type { CarePlanStatus } from '@/types'

export function NewOrderPage() {
  const createOrder = useCreateOrder()
  const [submittedPlan, setSubmittedPlan] = useState<{ id: number; status: CarePlanStatus } | null>(null)
  const [pendingData, setPendingData] = useState<OrderFormData | null>(null)

  const { register, handleSubmit, reset, formState: { errors } } = useForm<OrderFormData>({
    resolver: zodResolver(orderSchema),
  })

  const onSuccess = (result: { care_plan_id: number; status: CarePlanStatus }) => {
    setSubmittedPlan({ id: result.care_plan_id, status: result.status })
    setPendingData(null)
    reset()
  }

  const onSubmit = (data: OrderFormData) => {
    setPendingData(null)
    createOrder.mutate(data, {
      onSuccess,
      onError: (error) => {
        if (error instanceof AppError && error.requires_confirmation) {
          setPendingData(data)
        }
      },
    })
  }

  const onConfirm = () => {
    if (!pendingData) return
    createOrder.mutate({ ...pendingData, confirm: true }, { onSuccess })
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Generate Care Plan</h1>

      {submittedPlan && (
        <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          <p className="font-medium">Order submitted successfully.</p>
          <p className="mt-1">
            Care Plan #{submittedPlan.id} has been added to the queue with status <span className="font-semibold">{submittedPlan.status}</span>.
          </p>
          <p className="mt-2">
            <Link to="/dashboard" className="text-blue-600 hover:underline">
              Open dashboard
            </Link>
            {' '}to monitor progress while you continue entering orders.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-lg shadow p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <FormField label="Patient First Name" required error={errors.first_name?.message}>
            <input
              {...register('first_name')}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>

          <FormField label="Patient Last Name" required error={errors.last_name?.message}>
            <input
              {...register('last_name')}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField label="MRN" hint="6-digit patient ID" required error={errors.mrn?.message}>
            <input
              {...register('mrn')}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>

          <FormField label="Date of Birth" required error={errors.dob?.message}>
            <input
              type="date"
              {...register('dob')}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField label="Referring Provider" required error={errors.referring_provider?.message}>
            <input
              {...register('referring_provider')}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>

          <FormField label="Provider NPI" hint="10-digit NPI" required error={errors.referring_provider_npi?.message}>
            <input
              {...register('referring_provider_npi')}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>
        </div>

        <FormField label="Primary Diagnosis (ICD-10)" hint="e.g. M05.79" required error={errors.primary_diagnosis?.message}>
          <input
            {...register('primary_diagnosis')}
            placeholder="e.g. M05.79"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </FormField>

        <FormField label="Medication Name" required error={errors.medication_name?.message}>
          <input
            {...register('medication_name')}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </FormField>

        <FormField label="Additional Notes" hint="Medication history, allergies, other diagnoses...">
          <textarea
            {...register('additional_notes')}
            rows={3}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          />
        </FormField>

        {createOrder.error instanceof AppError && (
          createOrder.error.requires_confirmation ? (
            <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4 text-sm text-yellow-800">
              <p className="font-medium">{createOrder.error.message}</p>
              <ul className="mt-2 list-disc pl-4 space-y-1">
                {createOrder.error.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
              <Button
                type="button"
                onClick={onConfirm}
                disabled={createOrder.isPending}
                className="mt-3"
              >
                Confirm and Submit
              </Button>
            </div>
          ) : (
            <p className="text-sm text-red-600">{createOrder.error.message}</p>
          )
        )}

        <Button type="submit" disabled={createOrder.isPending} className="w-full justify-center py-2.5">
          {createOrder.isPending ? 'Submitting...' : 'Generate Care Plan'}
        </Button>
      </form>
    </div>
  )
}
