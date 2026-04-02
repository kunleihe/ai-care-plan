export type CarePlanStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface CarePlan {
  id: number
  status: CarePlanStatus
  content: string | null
  patient: {
    first_name: string
    last_name: string
    mrn: string
  }
  order: {
    medication: string
    diagnosis: string
    referring_provider: string
  }
}

export interface OrderCreateData {
  first_name: string
  last_name: string
  mrn: string
  dob: string
  referring_provider: string
  referring_provider_npi: string
  primary_diagnosis: string
  medication_name: string
  additional_notes?: string
}

export interface OrderCreateResponse {
  care_plan_id: number
}
