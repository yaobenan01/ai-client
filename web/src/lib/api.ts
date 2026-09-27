const BASE = ''

function token(): string | null {
  return localStorage.getItem('ai-client-token')
}

export function setToken(t: string | null) {
  if (t) localStorage.setItem('ai-client-token', t)
  else localStorage.removeItem('ai-client-token')
}

async function request<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(opts.headers as any) }
  const t = token()
  if (t) headers.Authorization = `Bearer ${t}`
  const res = await fetch(BASE + path, { ...opts, headers })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || `请求失败 (${res.status})`)
  return data as T
}

export const api = {
  health: () => request('/health'),
  register: (username: string, password: string) => request('/api/auth/register', { method: 'POST', body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) => request<{ token: string; user: any }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request<{ user: any }>('/api/auth/me'),
  listModels: () => request<{ models: any[]; default: string | null }>('/api/models'),
  addModel: (m: any) => request('/api/models', { method: 'POST', body: JSON.stringify(m) }),
  importModel: (path: string, name?: string) => request('/api/models/import', { method: 'POST', body: JSON.stringify({ path, name }) }),
  runtimes: () => request<{ runtimes: any }>('/api/system/runtimes'),
  removeModel: (id: string) => request(`/api/models/${id}`, { method: 'DELETE' }),
  setDefaultModel: (id: string) => request(`/api/models/${id}/default`, { method: 'POST' }),
  listTasks: () => request<{ tasks: any[] }>('/api/tasks'),
  createTask: (payload: { title: string; input: string; model_id?: string }) => request<{ task: any }>('/api/tasks', { method: 'POST', body: JSON.stringify(payload) }),
  getTask: (id: string) => request<{ task: any }>(`/api/tasks/${id}`),
  runTask: (id: string) => request(`/api/tasks/${id}/run`, { method: 'POST' }),
  listPlugins: () => request<{ plugins: any[] }>('/api/plugins'),
  installPlugin: (path: string) => request('/api/plugins/install', { method: 'POST', body: JSON.stringify({ path }) }),
  systemInfo: () => request('/api/system/info')
}

