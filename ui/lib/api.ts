import axios from "axios"

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json"
  }
})

// Add response interceptor to suppress console errors for expected failures
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Suppress network errors completely (backend offline/cloud mode)
    const isNetworkError =
      error.code === 'ERR_NETWORK' ||
      error.message === 'Network Error' ||
      !error.response  // No response = connection failure

    // Silent endpoints: Don't log errors for initial connection checks
    const silentEndpoints = ['/providers', '/system/health']
    const isSilentEndpoint = silentEndpoints.some(endpoint =>
      error.config?.url?.includes(endpoint)
    )

    // Only log unexpected, non-network errors
    if (!isNetworkError && !isSilentEndpoint && error.response?.status !== 404) {
      console.error('API Error:', error.message)
    }

    return Promise.reject(error)
  }
)

// Project endpoints
export const projectAPI = {
  createProject: async (formData: FormData, token?: string) => {
    const headers: Record<string, string> = { "Content-Type": "multipart/form-data" }
    if (token) headers["Authorization"] = `Bearer ${token}`

    const res = await api.post("/projects", formData, { headers })
    return res.data
  },

  getProjects: async (token?: string) => {
    const headers: Record<string, string> = {}
    if (token) headers["Authorization"] = `Bearer ${token}`

    const res = await api.get("/projects", { headers })
    return res.data
  },

  getProject: async (projectId: number, token?: string) => {
    const headers: Record<string, string> = {}
    if (token) headers["Authorization"] = `Bearer ${token}`

    const res = await api.get(`/projects/${projectId}`, { headers })
    return res.data
  },

  deleteProject: async (projectId: number, token?: string) => {
    const headers: Record<string, string> = {}
    if (token) headers["Authorization"] = `Bearer ${token}`

    const res = await api.delete(`/projects/${projectId}`, { headers })
    return res.data
  },

  getDownloadUrl: async (projectId: number, token?: string) => {
    const headers: Record<string, string> = {}
    if (token) headers["Authorization"] = `Bearer ${token}`

    const res = await api.get(`/projects/${projectId}/download`, { headers })
    return res.data
  }
}

// Provider endpoints
export const providerAPI = {
  getProviders: async () => {
    const res = await api.get("/providers")
    return res.data
  },

  getProviderModels: async (providerName: string) => {
    const res = await api.get(`/providers/${providerName}/models`)
    return res.data
  }
}

// Auth endpoints
export const authAPI = {
  register: async (email: string, password: string) => {
    const res = await api.post("/api/v1/auth/register", { email, password })
    return res.data
  }
}

// Health check
export const healthCheck = async () => {
  const res = await api.get("/health")
  return res.data
}
