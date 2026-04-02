import api from './api'
import type { CarePlan, OrderCreateData, OrderCreateResponse } from '@/types'

export const orderService = {
  createOrder: async (data: OrderCreateData): Promise<OrderCreateResponse> => {
    const response = await api.post<OrderCreateResponse>('/orders/', data)
    return response.data
  },
}

export const carePlanService = {
  getStatus: async (planId: string | number): Promise<CarePlan> => {
    const response = await api.get<CarePlan>(`/care-plans/${planId}/`)
    return response.data
  },
}
