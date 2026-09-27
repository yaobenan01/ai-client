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
    setModels(r.models); setDef(r.default)
  }, [])
  const loadRuntimes = useCallback(async () => {
    try { const r = await api.runtimes(); setRuntimes(r.runtimes) } catch {}
  }, [])
  useEffect(() => { load().catch(() => {}); loadRuntimes() }, [load, loadRuntimes])

  async function add(e: React.FormEvent) {
    e.preventDefault(); setMsg('')
    try { await api.addModel({ name, kind, config: { base_url: baseUrl, model } }); setName(''); setModel(''); await load() }
    catch (err: any) { setMsg(err.message) }
  }
  async function importModel(e: React.FormEvent) {
    e.preventDefault(); setMsg('')
    try { await api.importModel(importPath, importName || undefined); setImportPath(''); setImportName(''); await load() }
    catch (err: any) { setMsg(err.message) }
  }
  async function remove(id: string) { await api.removeModel(id); await load() }
  async function setDefault(id: string) { await api.setDefaultModel(id); await load() }

  const rt = runtimes || {}
  const Rt = ({ on, label }: { on: boolean; label: string }) => (
    <span className="badge" style={{ background: on ? 'var(--ok-soft)' : 'var(--bg-2)', color: on ? 'var(--ok)' : 'var(--muted)' }}>
      <i className={`status-dot ${on ? 'on' : 'off'}`} style={{ width: 7, height: 7, borderRadius: '50%', background: on ? 'var(--ok)' : 'var(--border-2)' }} />
      {label}
    </span>
  )

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>大模型</h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>接入本地 GGUF / ONNX 模型，或任何 OpenAI 兼容本地端点</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>运行时状态</h3>
        <div className="row" style={{ gap: 10 }}>
          <Rt on={!!rt.llama_server} label="llama.cpp" />
          <Rt on={!!rt.python} label="Python" />
          <Rt on={!!rt.ppt_master} label="ppt-master" />
          <Rt on={!!rt.libreoffice} label="LibreOffice" />
          <Rt on={!!rt.ffmpeg} label="FFmpeg" />
          <span className="badge pending"><i className="dot" />TTS：{rt.tts_engine || '未配置'}</span>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>✦ 导入本地模型</h3>
          <form onSubmit={importModel}>
            <div className="field"><label>模型文件路径（.gguf / .onnx）</label>
              <input className="input" value={importPath} onChange={(e) => setImportPath(e.target.value)} placeholder="D:\models\qwen2.5-7b-instruct-q4.gguf" required />
            </div>
            <div className="field"><label>显示名称（可选）</label>
              <input className="input" value={importName} onChange={(e) => setImportName(e.target.value)} placeholder="Qwen 7B" />
            </div>
            <button className="btn">导入并自动拉起</button>
          </form>
        </div>

        <div className="card">
          <h3>添加兼容端点</h3>
          <form onSubmit={add}>
            <div className="field"><label>模型名称</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="本地 Qwen 7B" required />
            </div>
            <div className="field"><label>类型</label>
              <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="local_gguf">本地 GGUF（llama.cpp）</option>
                <option value="openai_compat">OpenAI 兼容端点</option>
              </select>
            </div>
            <div className="row">
              <div className="field" style={{ flex: 1 }}><label>API 地址</label>
                <input className="input" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
              </div>
              <div className="field" style={{ flex: 1 }}><label>模型 ID</label>
                <input className="input" value={model} onChange={(e) => setModel(e.target.value)} placeholder="model id" />
              </div>
            </div>
            <button className="btn">添加模型</button>
          </form>
        </div>
      </div>

      {msg && <p className="muted" style={{ color: 'var(--err)', marginTop: 12 }}>{msg}</p>}

      <div className="grid" style={{ marginTop: 16 }}>
        {models.map((m) => (
          <div className="card" key={m.id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong style={{ fontSize: 15 }}>{m.name}</strong>
              {m.id === def ? <span className="badge done"><i className="dot" />默认</span> : <span className="badge pending"><i className="dot" />{m.kind}</span>}
            </div>
            <div className="kv"><span>类型</span><span className="mono">{m.kind}</span></div>
            <div className="kv"><span>配置</span><span className="mono" style={{ overflowWrap: 'anywhere', maxWidth: 220, textAlign: 'right' }}>{JSON.stringify(m.config)}</span></div>
            <div className="row" style={{ marginTop: 12 }}>
              {m.id !== def && <button className="btn ghost sm" onClick={() => setDefault(m.id)}>设为默认</button>}
              <button className="btn danger sm" onClick={() => remove(m.id)}>删除</button>
            </div>
          </div>
        ))}
        {models.length === 0 && <div className="empty" style={{ gridColumn: '1 / -1' }}>尚未配置模型，导入 .gguf 或添加本地端点即可使用</div>}
      </div>
    </div>
  )
}
