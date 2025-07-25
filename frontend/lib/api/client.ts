import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor para adicionar token
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const authStore = localStorage.getItem('auth-storage')
    if (authStore) {
      try {
        const parsed = JSON.parse(authStore)
        const token = parsed.state?.token
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      } catch (e) {
        console.error('Error parsing auth store:', e)
      }
    }
  }
  return config
})

// Interceptor para tratar erros
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('auth-storage')
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

export const adminApi = {
  getAdminStats: async () => {
    const response = await apiClient.get('/api/v1/admin/stats')
    return response.data
  },
  getAllUsers: async () => {
    const response = await apiClient.get('/api/v1/admin/users')
    return response.data
  },
  getCustomEndpoints: async () => {
    const response = await apiClient.get('/api/v1/admin/endpoints')
    return response.data
  }
}