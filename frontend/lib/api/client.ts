import axios from 'axios'
import { useAuthStore } from '@/lib/store/auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor para adicionar token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para tratar erros
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API Functions
export const authApi = {
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { email, password })
    return response.data
  },
  register: async (data: any) => {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  },
  refreshToken: async () => {
    const response = await apiClient.post('/auth/refresh')
    return response.data
  }
}

export const enrichmentApi = {
  enrichCompany: async (data: any) => {
    const response = await apiClient.post('/api/v1/enrich/company', data)
    return response.data
  },
  enrichPerson: async (data: any) => {
    const response = await apiClient.post('/api/v1/enrich/person', data)
    return response.data
  },
  getDashboardStats: async () => {
    const response = await apiClient.get('/api/v1/dashboard/stats')
    return response.data
  }
}

export const billingApi = {
  getPlans: async () => {
    const response = await apiClient.get('/api/v1/billing/plans')
    return response.data
  },
  createCheckoutSession: async (planId: string) => {
    const response = await apiClient.post('/api/v1/billing/checkout', { planId })
    return response.data
  },
  getInvoices: async () => {
    const response = await apiClient.get('/api/v1/billing/invoices')
    return response.data
  }
}