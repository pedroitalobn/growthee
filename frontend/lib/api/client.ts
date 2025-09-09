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
  login: async (emailOrUsername: string, password: string) => {
    const response = await apiClient.post('/api/v1/auth/login', { emailOrUsername, password })
    return response.data
  },
  register: async (data: any) => {
    const response = await apiClient.post('/api/v1/auth/register', data)
    return response.data
  },
  refreshToken: async () => {
    const response = await apiClient.post('/api/v1/auth/refresh')
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
  },
  // Plan management
  getAllPlans: async () => {
    const response = await apiClient.get('/api/v1/admin/plans')
    return response.data
  },
  getPlanStats: async () => {
    const response = await apiClient.get('/api/v1/admin/plans/stats')
    return response.data
  },
  togglePlanStatus: async (planId: string, active: boolean) => {
    const response = await apiClient.post(`/api/v1/admin/plans/${planId}/toggle`, { active })
    return response.data
  },
  getAllSubscriptions: async () => {
    const response = await apiClient.get('/api/v1/admin/subscriptions')
    return response.data
  },
  cancelSubscription: async (subscriptionId: string) => {
    const response = await apiClient.post(`/api/v1/admin/subscriptions/${subscriptionId}/cancel`)
    return response.data
  },
  // Credit management
  getCreditTransactions: async () => {
    const response = await apiClient.get('/api/v1/admin/credits/transactions')
    return response.data
  },
  getCreditStats: async () => {
    const response = await apiClient.get('/api/v1/admin/credits/stats')
    return response.data
  },
  // Endpoint management
  getAllEndpoints: async () => {
    const response = await apiClient.get('/api/v1/admin/endpoints')
    return response.data
  },
  getEndpointStats: async () => {
    const response = await apiClient.get('/api/v1/admin/endpoints/stats')
    return response.data
  },
  createEndpoint: async (endpoint: any) => {
    const response = await apiClient.post('/api/v1/admin/endpoints', endpoint)
    return response.data
  },
  updateEndpoint: async (endpointId: string, endpoint: any) => {
    const response = await apiClient.put(`/api/v1/admin/endpoints/${endpointId}`, endpoint)
    return response.data
  },
  deleteEndpoint: async (endpointId: string) => {
    const response = await apiClient.delete(`/api/v1/admin/endpoints/${endpointId}`)
    return response.data
  },
  toggleEndpointStatus: async (endpointId: string, active: boolean) => {
    const response = await apiClient.post(`/api/v1/admin/endpoints/${endpointId}/toggle`, { active })
    return response.data
  },
  // Super Admin Methods
  getSystemStats: async () => {
    const response = await apiClient.get('/api/v1/admin/system/stats')
    return response.data
  },
  getSystemEndpoints: async () => {
    const response = await apiClient.get('/api/v1/admin/system/endpoints')
    return response.data
  },
  getSystemFeatures: async () => {
    const response = await apiClient.get('/api/v1/admin/system/features')
    return response.data
  },
  getUsageStats: async (days: number) => {
    const response = await apiClient.get(`/api/v1/admin/usage/stats?days=${days}`)
    return response.data
  },
  toggleMaintenanceMode: async (enabled: boolean) => {
    const response = await apiClient.post('/api/v1/admin/system/maintenance', { enabled })
    return response.data
  },
  // User Management
  createUser: async (userData: any) => {
    const response = await apiClient.post('/api/v1/admin/users', userData)
    return response.data
  },
  updateUser: async (userId: string, userData: any) => {
    const response = await apiClient.put(`/api/v1/admin/users/${userId}`, userData)
    return response.data
  },
  deleteUser: async (userId: string) => {
    const response = await apiClient.delete(`/api/v1/admin/users/${userId}`)
    return response.data
  },
  toggleUserStatus: async (userId: string) => {
    const response = await apiClient.post(`/api/v1/admin/users/${userId}/toggle-status`)
    return response.data
  },
  changeUserPlan: async (userId: string, planId: string) => {
    const response = await apiClient.post(`/api/v1/admin/users/${userId}/change-plan`, { planId })
    return response.data
  },
  // Credit Management
  addCredits: async (userId: string, amount: number, reason?: string) => {
    const response = await apiClient.post(`/api/v1/admin/users/${userId}/credits/add`, { amount, reason })
    return response.data
  },
  removeCredits: async (userId: string, amount: number, reason?: string) => {
    const response = await apiClient.post(`/api/v1/admin/users/${userId}/credits/remove`, { amount, reason })
    return response.data
  },
  getCreditHistory: async (userId?: string) => {
    const url = userId ? `/api/v1/admin/credits/history?userId=${userId}` : '/api/v1/admin/credits/history'
    const response = await apiClient.get(url)
    return response.data
  },
  // Plan Management
  createPlan: async (planData: any) => {
    const response = await apiClient.post('/api/v1/admin/plans', planData)
    return response.data
  },
  updatePlan: async (planId: string, planData: any) => {
    const response = await apiClient.put(`/api/v1/admin/plans/${planId}`, planData)
    return response.data
  },
  deletePlan: async (planId: string) => {
    const response = await apiClient.delete(`/api/v1/admin/plans/${planId}`)
    return response.data
  },
  togglePlan: async (planId: string) => {
    const response = await apiClient.post(`/api/v1/admin/plans/${planId}/toggle`)
    return response.data
  },
  // Endpoint Management
  toggleEndpoint: async (endpointId: string) => {
    const response = await apiClient.post(`/api/v1/admin/system/endpoints/${endpointId}/toggle`)
    return response.data
  },
  updateEndpointCost: async (endpointId: string, creditCost: number) => {
    const response = await apiClient.put(`/api/v1/admin/system/endpoints/${endpointId}/cost`, { creditCost })
    return response.data
  },
  toggleFeature: async (featureId: string) => {
    const response = await apiClient.post(`/api/v1/admin/features/${featureId}/toggle`)
    return response.data
  },
  
  // System Health & Maintenance
  getSystemHealth: async () => {
    const response = await apiClient.get('/api/v1/admin/system/health')
    return response.data
  },
  getMaintenanceMode: async () => {
    const response = await apiClient.get('/api/v1/admin/system/maintenance-mode')
    return response.data
  },
  clearSystemCache: async () => {
    const response = await apiClient.post('/api/v1/admin/system/clear-cache')
    return response.data
  },
  
  // API Usage Dashboard functions
  getAPIUsageStats: async () => {
    const response = await apiClient.get('/api/v1/admin/api-usage/stats')
    return response.data
  },
  getAPIServices: async () => {
    const response = await apiClient.get('/api/v1/admin/api-usage/services')
    return response.data
  },
  getAPILogs: async (params?: { service?: string; limit?: number; start_date?: string; end_date?: string }) => {
    const response = await apiClient.get('/api/v1/admin/api-usage/logs', { params })
    return response.data
  },
  clearAPILogs: async () => {
    const response = await apiClient.delete('/api/v1/admin/api-usage/logs')
    return response.data
  },
  getAPIAlertsummary: async () => {
    const response = await apiClient.get('/api/v1/admin/api-alerts/summary')
    return response.data
  },
  checkServiceLimits: async (service: string) => {
    const response = await apiClient.get(`/api/v1/admin/api-alerts/check/${service}`)
    return response.data
  },
  testAlertSystem: async () => {
    const response = await apiClient.post('/api/v1/admin/api-alerts/test')
    return response.data
  }
}