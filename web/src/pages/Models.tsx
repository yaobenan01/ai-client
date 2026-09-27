import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'

export default function Models() {
  const [models, setModels] = useState<any[]>([])
  const [def, setDef] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [kind, setKind] = useState('local_gguf')
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8080/v1')
  const [model, setModel] = useState('')
  const [importPath, setImportPath] = useState('')
  const [importName, setImportName] = useState('')
  const [runtimes, setRuntimes] = useState<any>(null)
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => {
    const r = await api.listModels()
    setModels(r.models)
    setDef(r.default)
  }, [])

  const loadRuntimes = useCallback(async () => {
    try {
      const r = await api.runtimes()
      setRuntimes(r.runtimes)
    } catch {}
  }, [])

  useEffect(() => { load().catch(() => {}); loadRuntimes() }, [load, loadRuntimes])

  async function add(e: React.FormEvent) {
    e.preventDefault()
    setMsg('')
    try {
      await api.addModel({ name, kind, config: { base_url: baseUrl, model } })
      setName(''); setModel('')
      await load()
    } catch (err: any) { setMsg(err.message) }
  }

  async function importModel(e: React.FormEvent) {
    e.preventDefault()
    setMsg('')
    try {
      await api.importModel(importPath, importName || undefined)
      setImportPath(''); setImportName('')
      await load()
    } catch (err: any) { setMsg(err.message) }
  }

  async function remove(id: string) { await api.removeModel(id); await load() }
  async function setDefault(id: string) { await api.setDefaultModel(id); await load() }

  const rt = runtimes || {}
  const ok = (v: any) => (v ? '✅' : '⬜')

  return (
    <div>
      <h1>大模型配置</h1>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>运行时状态</h3>
        <div className="row" style={{ gap: 18 }}>
          <span>{ok(rt.llama_server)} llama.cpp</span>
          <span>{ok(rt.python)} Python</span>
          <span>{ok(rt.ppt_master)} ppt-master</span>
          <span>{ok(rt.libreoffice)} LibreOffice</span>
          <span>{ok(rt.ffmpeg)} FFmpeg</span>
          <span className="muted">TTS: {rt.tts_engine || '-'}</span>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>导入本地模型（.gguf / .onnx，离线）</h3>
        <form onSubmit={importModel}>
          <div className="row">
            <div className="field" style={{ flex: 2 }}>
              <label>模型文件路径</label>
              <input className="input" value={importPath} onChange={(e) => setImportPath(e.target.value)} placeholder="D:\models\qwen2.5-7b-instruct-q4.gguf" required />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>显示名称（可选）</label>
              <input className="input" value={importName} onChange={(e) => setImportName(e.target.value)} placeholder="Qwen 7B" />
            </div>
          </div>
          <button className="btn">导入模型</button>
        </form>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>添加兼容端点</h3>
        <form onSubmit={add}>
          <div className="field">
            <label>模型名称</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="如：本地 Qwen 7B" required />
          </div>
          <div className="row">
            <div className="field" style={{ flex: 1 }}>
              <label>类型</label>
              <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="local_gguf">本地 GGUF（llama.cpp）</option>
                <option value="openai_compat">OpenAI 兼容端点（本地）</option>
              </select>
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>API 地址</label>
              <input className="input" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>模型 ID</label>
              <input className="input" value={model} onChange={(e) => setModel(e.target.value)} placeholder="model id" />
            </div>
          </div>
          <button className="btn">添加模型</button>
        </form>
      </div>

      {msg && <p className="muted" style={{ color: 'var(--err)' }}>{msg}</p>}

      <div className="grid">
        {models.map((m) => (
          <div className="card" key={m.id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>{m.name}</strong>
              {m.id === def && <span className="badge ok">默认</span>}
            </div>
            <p className="muted mono" style={{ overflowWrap: 'anywhere' }}>{m.kind}</p>
            <pre className="log" style={{ fontSize: 12 }}>{JSON.stringify(m.config, null, 2)}</pre>
            <div className="row">
              {m.id !== def && <button className="btn ghost" onClick={() => setDefault(m.id)}>设为默认</button>}
              <button className="btn danger" onClick={() => remove(m.id)}>删除</button>
            </div>
          </div>
        ))}
        {models.length === 0 && <p className="muted">尚未配置模型，请导入 .gguf 文件或添加本地端点。</p>}
      </div>
    </div>
  )
}
