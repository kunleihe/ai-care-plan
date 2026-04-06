import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// 统一处理错误，把后端的 code / message / warnings / requires_confirmation 带出来
export class AppError extends Error {
  code: string
  warnings: string[]
  requires_confirmation: boolean

  constructor(
    message: string,
    code = 'INTERNAL_ERROR',
    warnings: string[] = [],
    requires_confirmation = false,
  ) {
    super(message)
    this.code = code
    this.warnings = warnings
    this.requires_confirmation = requires_confirmation
  }
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error.response?.data
    const message = data?.message || error.message || 'An error occurred'
    const code = data?.code || 'INTERNAL_ERROR'
    const warnings = data?.warnings || []
    const requires_confirmation = data?.requires_confirmation || false
    throw new AppError(message, code, warnings, requires_confirmation)
  }
)

export default api
