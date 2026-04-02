import { useMutation, useQuery } from '@tanstack/react-query'
import { carePlanService, orderService } from '@/services/orderService'
import type { OrderCreateData } from '@/types'

export function useCreateOrder() {
  return useMutation({
    mutationFn: (data: OrderCreateData) => orderService.createOrder(data),
  })
}

/**
 * 轮询 care plan 状态，直到 completed 或 failed 为止
 * 这就是 Day 6 的核心：前端自动知道任务完成了
 */
export function useCarePlanStatus(planId: string | number) {
  return useQuery({
    queryKey: ['carePlan', planId],
    queryFn: () => carePlanService.getStatus(planId),
    enabled: !!planId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'pending' || status === 'processing') {
        return 3000 // 每 3 秒轮询一次
      }
      return false // completed / failed 停止轮询
    },
  })
}
