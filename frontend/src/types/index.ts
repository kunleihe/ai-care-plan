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

export interface CarePlanStatusResponse extends Pick<CarePlan, 'id' | 'status' | 'content' | 'patient' | 'order'> {
  error?: string
}

export interface CarePlanListItem {
  id: number
  status: CarePlanStatus
  patient_name: string
  mrn: string
  medication: string
  diagnosis: string
  created_at: string
  error?: string
}

export interface PaginatedCarePlansResponse {
  count: number
  next: number | null
  previous: number | null
  results: CarePlanListItem[]
}

export interface CarePlanBatchStatusItem {
  id: number
  status: CarePlanStatus
  error?: string
}

export interface CarePlanBatchStatusResponse {
  results: CarePlanBatchStatusItem[]
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
  status: CarePlanStatus
}
