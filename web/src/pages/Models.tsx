import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import ModelTestModal from '../components/ModelTestModal'

export default function Models() {
  const [models, setModels] = useState<any[]>([])
  const [def, setDef] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [kind, setKind] = useState('local_gguf')
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8080/v1')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [ctxLen, setCtxLen] = useState(4096)
  const [temperature, setTemperature] = useState(0.7)

  const [importPath, setImportPath] = useState('')
  const [importName, setImportName] = useState('')
  const [runtimes, setRuntimes] = useState<any>(null)
  const [msg, setMsg] = useState('')
  const [testingModel, setTestingModel] = useState<any>(null)

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

  useEffect(() => {
    load().catch(() => {})
    loadRuntimes()
  }, [load, loadRuntimes])

  async function add(e: React.FormEvent) {
    e.preventDefault()
    setMsg('')
    try {
      await api.addModel({
        name,
        kind,
        config: {
          base_url: baseUrl,
          model: model || 'default',
          api_key: apiKey ? apiKey : undefined,
          ctx_len: Number(ctxLen) || 4096,
          temperature: Number(temperature) || 0.7,
        },
      })
      setName('')
      setModel('')
      setApiKey('')
      await load()
    } catch (err: any) {
      setMsg(err.message)
    }
  }

  async function importModel(e: React.FormEvent) {
    e.preventDefault()
    setMsg('')
    try {
      await api.importModel(importPath, importName || undefined)
      setImportPath('')
      setImportName('')
      await load()
    } catch (err: any) {
      setMsg(err.message)
    }
  }

  async function remove(id: string) {
    if (!confirm('确认删除该模型配置吗？')) return
    await api.removeModel(id)
    await load()
  }

  async function setDefault(id: string) {
    await api.setDefaultModel(id)
    await load()
  }

  const rt = runtimes || {}
  const Rt = ({ on, label }: { on: boolean; label: string }) => (
    <span
      className="badge"
      style={{
        background: on ? 'var(--ok-soft)' : 'var(--bg-2)',
        color: on ? 'var(--ok)' : 'var(--muted)',
        border: '1px solid var(--border)',
      }}
    >
      <i
        className={`status-dot ${on ? 'on' : 'off'}`}
        style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: on ? 'var(--ok)' : 'var(--border-2)',
        }}
      />
      {label}: {on ? '已就绪' : '未检测到'}
    </span>
  )

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>大模型配置与诊断</h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            接入本地 GGUF / ONNX 模型，或本地 OpenAI 兼容端点（Ollama / vLLM / llama-server）
          </div>
        </div>

        <button className="btn ghost sm" onClick={loadRuntimes}>
          🔄 重新检测运行时
        </button>
      </div>

      {/* 运行时诊断卡片 */}
      <div className="card" style={{ marginBottom: 18 }}>
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>⚙️ 本地附件运行时环境</h3>
          <span className="muted" style={{ fontSize: 12 }}>
            语音引擎：{rt.tts_engine || 'cosyvoice'}
          </span>
        </div>

        <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
          <Rt on={!!rt.llama_server} label="llama.cpp 引擎" />
          <Rt on={!!rt.python} label="Python 3.10+ 环境" />
          <Rt on={!!rt.ppt_master} label="ppt-master 插件" />
          <Rt on={!!rt.libreoffice} label="LibreOffice 渲染器" />
          <Rt on={!!rt.ffmpeg} label="FFmpeg 合成器" />
        </div>
      </div>

      <div className="grid">
        {/* 导入本地 GGUF */}
        <div className="card">
          <h3>✦ 导入本地模型（GGUF / ONNX）</h3>
          <p className="muted" style={{ fontSize: 13, marginBottom: 14 }}>
            选择本地模型文件，系统将登记并在任务需要时通过内置 llama-server 自动拉起。
          </p>

          <form onSubmit={importModel}>
            <div className="field">
              <label>本地模型绝对路径</label>
              <input
                className="input"
                value={importPath}
                onChange={(e) => setImportPath(e.target.value)}
                placeholder="D:\models\qwen2.5-7b-instruct-q4.gguf"
                required
              />
            </div>
            <div className="field">
              <label>自定义显示名称（可选）</label>
              <input
                className="input"
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
                placeholder="Qwen 2.5 7B 本地版"
              />
            </div>
            <button className="btn">导入并登记档案</button>
          </form>
        </div>

        {/* 添加 OpenAI 兼容端点 */}
        <div className="card">
          <h3>添加本地兼容端点</h3>
          <p className="muted" style={{ fontSize: 13, marginBottom: 14 }}>
            连接本地运行的 Ollama (11434)、vLLM 或 llama.cpp 服务，零网络开销。
          </p>

          <form onSubmit={add}>
            <div className="row">
              <div className="field" style={{ flex: 1 }}>
                <label>模型显示名称</label>
                <input
                  className="input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="例如：本地 Qwen 7B"
                  required
                />
              </div>
              <div className="field" style={{ flex: 1 }}>
                <label>架构类型</label>
                <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
                  <option value="local_gguf">本地 GGUF（自动拉起）</option>
                  <option value="openai_compat">OpenAI 兼容端点</option>
                </select>
              </div>
            </div>

            <div className="row">
              <div className="field" style={{ flex: 2 }}>
                <label>API 端点地址</label>
                <input
                  className="input"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="http://127.0.0.1:8080/v1"
                  required
                />
              </div>
              <div className="field" style={{ flex: 1 }}>
                <label>Model ID</label>
                <input
                  className="input"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="qwen2.5-7b"
                />
              </div>
            </div>

            <div className="row">
              <div className="field" style={{ flex: 1 }}>
                <label>上下文长度 (Tokens)</label>
                <input
                  className="input"
                  type="number"
                  value={ctxLen}
                  onChange={(e) => setCtxLen(Number(e.target.value))}
                />
              </div>
              <div className="field" style={{ flex: 1 }}>
                <label>API Key（可选）</label>
                <input
                  className="input"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                />
              </div>
            </div>

            <button className="btn">保存模型档案</button>
          </form>
        </div>
      </div>

      {msg && <p className="muted" style={{ color: 'var(--err)', marginTop: 12 }}>{msg}</p>}

      {/* 已配置的模型列表 */}
      <h3 style={{ margin: '24px 0 14px' }}>已配置的模型档案 ({models.length})</h3>
      <div className="grid">
        {models.map((m) => {
          const isDef = m.id === def
          return (
            <div className="card" key={m.id} style={{ position: 'relative' }}>
              <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
                <strong style={{ fontSize: 16 }}>{m.name}</strong>
                {isDef ? (
                  <span className="badge done">
                    <i className="dot" />
                    默认推荐
                  </span>
                ) : (
                  <span className="badge pending">
                    <i className="dot" />
                    {m.kind}
                  </span>
                )}
              </div>

              <div className="kv">
                <span>模型类别</span>
                <span className="mono">{m.kind}</span>
              </div>
              <div className="kv">
                <span>模型参数</span>
                <span
                  className="mono"
                  style={{
                    overflowWrap: 'anywhere',
                    maxWidth: 240,
                    textAlign: 'right',
                    fontSize: 12,
                  }}
                >
                  {JSON.stringify(m.config)}
                </span>
              </div>

              <div className="row" style={{ marginTop: 16, justifyContent: 'space-between' }}>
                <button
                  className="btn sm"
                  style={{ background: 'var(--accent-soft)', color: 'var(--accent)', boxShadow: 'none' }}
                  onClick={() => setTestingModel(m)}
                >
                  ⚡ 测试连通性
                </button>

                <div className="row" style={{ gap: 6 }}>
                  {!isDef && (
                    <button className="btn ghost sm" onClick={() => setDefault(m.id)}>
                      设为默认
                    </button>
                  )}
                  <button className="btn danger sm" onClick={() => remove(m.id)}>
                    删除
                  </button>
                </div>
              </div>
            </div>
          )
        })}
        {models.length === 0 && (
          <div className="empty" style={{ gridColumn: '1 / -1' }}>
            尚未配置模型。导入 .gguf 模型文件或添加本地端点即可开始离线推理。
          </div>
        )}
      </div>

      {/* 连通性测试模态框 */}
      {testingModel && (
        <ModelTestModal model={testingModel} onClose={() => setTestingModel(null)} />
      )}
    </div>
  )
}
