import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useCreateOrder } from '@/hooks/useOrders'
import { FormField } from '@/components/forms/FormField'
import { Button } from '@/components/ui/Button'
import type { OrderCreateData } from '@/types'

export function NewOrderPage() {
  const navigate = useNavigate()
  const createOrder = useCreateOrder()

  const { register, handleSubmit, formState: { errors } } = useForm<OrderCreateData>()

  const onSubmit = (data: OrderCreateData) => {
    createOrder.mutate(data, {
      onSuccess: (result) => {
        navigate(`/care-plans/${result.care_plan_id}`)
      },
    })
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Generate Care Plan</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-lg shadow p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <FormField label="Patient First Name" required error={errors.first_name?.message}>
            <input
              {...register('first_name', { required: 'Required' })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>

          <FormField label="Patient Last Name" required error={errors.last_name?.message}>
            <input
              {...register('last_name', { required: 'Required' })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField label="MRN" hint="6-digit patient ID" required error={errors.mrn?.message}>
            <input
              {...register('mrn', { required: 'Required' })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>

          <FormField label="Date of Birth" required error={errors.dob?.message}>
            <input
              type="date"
              {...register('dob', { required: 'Required' })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField label="Referring Provider" required error={errors.referring_provider?.message}>
            <input
              {...register('referring_provider', { required: 'Required' })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>

          <FormField label="Provider NPI" hint="10-digit NPI" required error={errors.referring_provider_npi?.message}>
            <input
              {...register('referring_provider_npi', { required: 'Required' })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>
        </div>

        <FormField label="Primary Diagnosis (ICD-10)" hint="e.g. M05.79" required error={errors.primary_diagnosis?.message}>
          <input
            {...register('primary_diagnosis', { required: 'Required' })}
            placeholder="e.g. M05.79"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </FormField>

        <FormField label="Medication Name" required error={errors.medication_name?.message}>
          <input
            {...register('medication_name', { required: 'Required' })}
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

        {createOrder.error && (
          <p className="text-sm text-red-600">{createOrder.error.message}</p>
        )}

        <Button type="submit" disabled={createOrder.isPending} className="w-full justify-center py-2.5">
          {createOrder.isPending ? 'Submitting...' : 'Generate Care Plan'}
        </Button>
      </form>
    </div>
  )
}
