import api from './api'
import type {
  CarePlan,
  CarePlanBatchStatusResponse,
  CarePlanStatusResponse,
  OrderCreateData,
  OrderCreateResponse,
  PaginatedCarePlansResponse,
} from '@/types'

export const orderService = {
  createOrder: async (data: OrderCreateData): Promise<OrderCreateResponse> => {
    const response = await api.post<OrderCreateResponse>('/orders/', data)
    return response.data
  },
}

export const carePlanService = {
  getCarePlans: async (page = 1, pageSize = 20): Promise<PaginatedCarePlansResponse> => {
    const response = await api.get<PaginatedCarePlansResponse>('/careplans/', {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  getStatuses: async (ids: number[]): Promise<CarePlanBatchStatusResponse> => {
    const response = await api.post<CarePlanBatchStatusResponse>('/careplans/statuses/', { ids })
    return response.data
  },

  getCarePlan: async (planId: string | number): Promise<CarePlan> => {
    const response = await api.get<CarePlan>(`/care-plans/${planId}/`)
    return response.data
  },

  getStatus: async (planId: string | number): Promise<CarePlanStatusResponse> => {
    const response = await api.get<CarePlanStatusResponse>(`/careplan/${planId}/status/`)
    return response.data
  },
}
