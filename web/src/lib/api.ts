// 开发环境（vite dev）通过代理转发到 core；打包后（桌面/PWA）直连 127.0.0.1:8787。
const BASE = import.meta.env.PROD ? 'http://127.0.0.1:8787' : ''

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
  let res: Response
  try {
    res = await fetch(BASE + path, { ...opts, headers })
  } catch {
    throw new Error('无法连接核心服务，请确认 ai-client 核心已在 127.0.0.1:8787 启动')
  }
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
  testModel: (id: string, prompt?: string) => request<{ ok: boolean; id: string; name: string; kind: string; latency_ms: number; response: string; finish_reason: string }>(`/api/models/${id}/test`, { method: 'POST', body: JSON.stringify({ prompt }) }),
  runtimes: () => request<{ runtimes: any }>('/api/system/runtimes'),
  removeModel: (id: string) => request(`/api/models/${id}`, { method: 'DELETE' }),
  setDefaultModel: (id: string) => request(`/api/models/${id}/default`, { method: 'POST' }),
  listTasks: () => request<{ tasks: any[] }>('/api/tasks'),
  createTask: (payload: { title: string; input: string; model_id?: string }) => request<{ task: any }>('/api/tasks', { method: 'POST', body: JSON.stringify(payload) }),
  getTask: (id: string) => request<{ task: any }>(`/api/tasks/${id}`),
  runTask: (id: string) => request(`/api/tasks/${id}/run`, { method: 'POST' }),
  cancelTask: (id: string) => request(`/api/tasks/${id}/cancel`, { method: 'POST' }),
  deleteTask: (id: string) => request(`/api/tasks/${id}`, { method: 'DELETE' }),
  quickGeneratePpt: (payload: { input_path?: string; content?: string }) => request<{ ok: boolean; path: string; filename: string }>('/api/ppt/quick-generate', { method: 'POST', body: JSON.stringify(payload) }),
  quickRenderVideo: (payload: { pptx_path: string; output_path?: string }) => request<{ ok: boolean; path: string; filename: string }>('/api/ppt/quick-video', { method: 'POST', body: JSON.stringify(payload) }),
  listWorkspaceFiles: () => request<{ files: Array<{ name: string; path: string; ext: string; size: number; modified: number }> }>('/api/workspace/files'),
  getArtifactUrl: (relPath: string) => `${BASE}/api/workspace/download/${encodeURIComponent(relPath.replace(/^\/+/, ''))}`,
  listPlugins: () => request<{ plugins: any[] }>('/api/plugins'),
  installPlugin: (path: string) => request('/api/plugins/install', { method: 'POST', body: JSON.stringify({ path }) }),
  systemInfo: () => request('/api/system/info')
}
