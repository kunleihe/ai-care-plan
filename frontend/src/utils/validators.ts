import { z } from 'zod'

export const orderSchema = z.object({
  first_name: z.string().min(1, 'First name is required'),

  last_name: z.string().min(1, 'Last name is required'),

  mrn: z
    .string()
    .regex(/^\d{6}$/, 'MRN must be exactly 6 digits'),

  dob: z.string().min(1, 'Date of birth is required'),

  referring_provider: z.string().min(1, 'Provider name is required'),

  referring_provider_npi: z
    .string()
    .regex(/^\d{10}$/, 'NPI must be exactly 10 digits'),

  primary_diagnosis: z
    .string()
    .regex(/^[A-Z]\d{2}(\.\d{1,4})?$/i, 'Must be a valid ICD-10 code (e.g. M05.79, I10)'),

  medication_name: z.string().min(1, 'Medication name is required'),

  additional_notes: z.string().optional(),

  confirm: z.boolean().optional(),
})

export type OrderFormData = z.infer<typeof orderSchema>
