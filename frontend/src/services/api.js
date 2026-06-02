import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach auth token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 by clearing session
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
  register: (data) => api.post('/auth/register', data),
}

// ─── Companies ───────────────────────────────────────────────────────────────
export const companiesApi = {
  list: (activeOnly = true) => api.get('/companies', { params: { active_only: activeOnly } }),
  get: (id) => api.get(`/companies/${id}`),
  create: (data) => api.post('/companies', data),
  update: (id, data) => api.put(`/companies/${id}`, data),
  delete: (id) => api.delete(`/companies/${id}`),
  refresh: (id) => api.post(`/companies/${id}/refresh`),
}

// ─── Signals ─────────────────────────────────────────────────────────────────
export const signalsApi = {
  list: (params = {}) => api.get('/signals', { params }),
  get: (id) => api.get(`/signals/${id}`),
  update: (id, data) => api.patch(`/signals/${id}`, data),
  count: (params = {}) => api.get('/signals/count', { params }),
  unreadCount: () => api.get('/signals/unread-count'),
  markAllRead: (companyId) =>
    api.post('/signals/mark-all-read', null, { params: companyId ? { company_id: companyId } : {} }),
}

// ─── Reports ─────────────────────────────────────────────────────────────────
export const reportsApi = {
  list: () => api.get('/reports'),
  get: (id) => api.get(`/reports/${id}`),
  generate: (month, year) => api.post('/reports/generate', { month, year }),
  generateCurrentMonth: () => api.post('/reports/generate/current-month'),
  delete: (id) => api.delete(`/reports/${id}`),
}

// ─── Admin ────────────────────────────────────────────────────────────────────
export const adminApi = {
  schedulerStatus: () => api.get('/admin/scheduler/status'),
  triggerDailyJob: () => api.post('/admin/trigger-daily-job'),
}

export default api
