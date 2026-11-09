import { useCallback, useEffect, useRef, useState } from 'react'
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

  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    const r = await api.listModels()
    setModels(r.models || [])
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

  function handleModelFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const path = (file as any).path || file.name
    setImportPath(path)
    if (!importName) {
      const baseName = file.name.replace(/\.(gguf|bin|onnx)$/i, '')
      setImportName(baseName)
    }
    e.target.value = ''
  }

  async function add(e: React.FormEvent) {
    e.preventDefault()
    setMsg('')
    try {
      await api.addModel({
        name: name.trim(),
        kind,
        config: {
          base_url: baseUrl.trim(),
          model: model.trim() || 'default',
          api_key: apiKey ? apiKey.trim() : undefined,
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
    if (!importPath.trim()) return
    setMsg('')
    try {
      await api.importModel(importPath.trim(), importName.trim() || undefined)
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
        background: on ? 'rgba(16, 185, 129, 0.1)' : 'var(--bg-2)',
        color: on ? '#059669' : 'var(--muted)',
        border: '1px solid ' + (on ? 'rgba(16, 185, 129, 0.25)' : 'var(--border)'),
        padding: '4px 11px',
        fontSize: '12px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        whiteSpace: 'nowrap'
      }}
    >
      <i
        className={`status-dot ${on ? 'on' : 'off'}`}
        style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: on ? '#10b981' : 'var(--border-2)',
        }}
      />
      {label}: {on ? '已就绪' : '未检测到'}
    </span>
  )

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto' }}>
      {/* 隐藏的本地模型文件选择器 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".gguf,.bin,.onnx"
        style={{ display: 'none' }}
        onChange={handleModelFileChange}
      />

      <div className="page-head" style={{ marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: '0 0 6px' }}>大模型配置与运行诊断</h1>
          <div className="muted" style={{ fontSize: 13.5 }}>
            接入本地 GGUF / ONNX 离线推理模型，或本地兼容端点（Ollama / vLLM / llama-server）
          </div>
        </div>

        <button className="btn ghost sm" style={{ padding: '8px 14px', whiteSpace: 'nowrap' }} onClick={loadRuntimes}>
          🔄 重新检测运行时
        </button>
      </div>

      {/* 运行时诊断卡片 */}
      <div className="card" style={{ marginBottom: 24, padding: '18px 22px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>⚙️</span> 本地附件运行时环境状态
          </h3>
          <span className="muted" style={{ fontSize: 12 }}>
            默认语音引擎：<strong>{rt.tts_engine || 'auto (智能双擎)'}</strong>
          </span>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <Rt on={!!rt.llama_server} label="llama.cpp 引擎" />
          <Rt on={!!rt.python} label="Python 3.10+ 环境" />
          <Rt on={!!rt.ppt_master} label="ppt-master 插件" />
          <Rt on={!!rt.libreoffice} label="LibreOffice 渲染器" />
          <Rt on={!!rt.ffmpeg} label="FFmpeg 合成器" />
          <Rt on={true} label="Avatar 数字人引擎" />
        </div>
      </div>

      {/* 模型导入与配置两列舒展工作台（比例均衡，拒绝单侧挤压） */}
      <div className="models-workbench">
        {/* 模块 1: 导入本地 GGUF/ONNX */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ marginBottom: 14 }}>
            <h3 style={{ margin: '0 0 8px', fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>✦</span> 导入本地模型（GGUF / ONNX）
            </h3>
            <p className="muted" style={{ fontSize: 13, lineHeight: 1.5, margin: 0 }}>
              选择本地模型文件，系统将自动登记并在任务执行时由内置 llama-server 免安装引擎拉起。
            </p>
          </div>

          <form onSubmit={importModel} style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            <div className="field" style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>本地模型绝对路径</label>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input
                  className="input"
                  style={{ flex: 1, minWidth: 0, height: 40 }}
                  value={importPath}
                  onChange={(e) => setImportPath(e.target.value)}
                  placeholder="可直接选择本地 .gguf 文件或手动输入路径"
                  required
                />
                <button
                  type="button"
                  className="btn ghost"
                  style={{ flexShrink: 0, padding: '9px 14px', whiteSpace: 'nowrap', height: 40 }}
                  onClick={() => fileInputRef.current?.click()}
                  title="从本地磁盘浏览并选择模型文件"
                >
                  📁 浏览文件
                </button>
              </div>
            </div>

            <div className="field" style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>自定义显示名称（可选）</label>
              <input
                className="input"
                style={{ width: '100%', height: 40 }}
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
                placeholder="例如：Qwen 2.5 7B 本地版"
              />
            </div>

            <div style={{ marginTop: 'auto', paddingTop: 10 }}>
              <button className="btn" style={{ width: '100%', height: 42, justifyContent: 'center', fontWeight: 600 }}>
                📥 导入并登记模型档案
              </button>
            </div>
          </form>
        </div>

        {/* 模块 2: 添加本地兼容端点 */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ marginBottom: 14 }}>
            <h3 style={{ margin: '0 0 8px', fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>🔌</span> 添加本地兼容端点 (OpenAI / Ollama)
            </h3>
            <p className="muted" style={{ fontSize: 13, lineHeight: 1.5, margin: 0 }}>
              连接本地运行的 Ollama (11434)、vLLM 或外部 OpenAI 兼容服务，支持零网络本地开销。
            </p>
          </div>

          <form onSubmit={add} style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.15fr)', gap: 14, marginBottom: 14 }}>
              <div className="field" style={{ margin: 0 }}>
                <label style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>模型显示名称</label>
                <input
                  className="input"
                  style={{ height: 40, width: '100%' }}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="例如：本地 Qwen 2.5 7B"
                  required
                />
              </div>

              <div className="field" style={{ margin: 0 }}>
                <label style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>架构类型</label>
                <select
                  className="input"
                  style={{ height: 40, width: '100%' }}
                  value={kind}
                  onChange={(e) => setKind(e.target.value)}
                >
                  <option value="local_gguf">本地 GGUF (llama.cpp)</option>
                  <option value="openai_compat">OpenAI 兼容协议</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(0, 1fr)', gap: 14, marginBottom: 14 }}>
              <div className="field" style={{ margin: 0 }}>
                <label style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>API 端点地址</label>
                <input
                  className="input"
                  style={{ height: 40, width: '100%' }}
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="http://127.0.0.1:8080/v1"
                  required
                />
              </div>

              <div className="field" style={{ margin: 0 }}>
                <label style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>Model ID</label>
                <input
                  className="input"
                  style={{ height: 40, width: '100%' }}
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="qwen2.5-7b"
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.25fr)', gap: 14, marginBottom: 20 }}>
              <div className="field" style={{ margin: 0 }}>
                <label style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>上下文长度 (Tokens)</label>
                <input
                  className="input"
                  style={{ height: 40, width: '100%' }}
                  type="number"
                  value={ctxLen}
                  onChange={(e) => setCtxLen(Number(e.target.value))}
                />
              </div>

              <div className="field" style={{ margin: 0 }}>
                <label style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>API Key（可选）</label>
                <input
                  className="input"
                  style={{ height: 40, width: '100%' }}
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="未设置或 sk-..."
                />
              </div>
            </div>

            <div style={{ marginTop: 'auto', paddingTop: 10 }}>
              <button className="btn" style={{ width: '100%', height: 42, justifyContent: 'center', fontWeight: 600 }}>
                💾 保存并接入模型档案
              </button>
            </div>
          </form>
        </div>
      </div>

      {msg && (
        <div style={{ padding: '12px 16px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: '#dc2626', borderRadius: 10, marginBottom: 20, fontSize: 13 }}>
          ⚠️ {msg}
        </div>
      )}

      {/* 已配置的模型列表（整齐等高栅格 + 标签规范化展示） */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '28px 0 16px' }}>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>📚</span> 已配置的模型档案 ({models.length})
        </h3>
        <span className="muted" style={{ fontSize: 12 }}>
          支持一键测试端点响应延迟与设为全局默认执行器
        </span>
      </div>

      <div className="models-grid">
        {models.map((m) => {
          const isDef = m.id === def
          const cfg = m.config || {}
          return (
            <div
              className="card"
              key={m.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                height: '100%',
                padding: '20px 22px',
                border: isDef ? '1.5px solid var(--accent)' : '1px solid var(--border)',
                background: isDef ? 'linear-gradient(180deg, rgba(99, 102, 241, 0.03) 0%, #fff 100%)' : '#fff',
                boxShadow: isDef ? '0 6px 20px rgba(99, 102, 241, 0.08)' : 'var(--shadow)'
              }}
            >
              <div>
                {/* 顶部标题与状态标签：一行舒展，杜绝折行挤压 */}
                <div className="task-card-header" style={{ marginBottom: 12 }}>
                  <strong className="task-card-title" style={{ fontSize: 16 }} title={m.name}>
                    {m.name}
                  </strong>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    {isDef && (
                      <span className="task-badge done">
                        <i className="dot" />
                        默认推荐
                      </span>
                    )}
                    <span className="task-badge pending">
                      {m.kind === 'local_gguf' ? '本地 GGUF' : 'OpenAI 协议'}
                    </span>
                  </div>
                </div>

                {/* 结构化参数规格卡片：拒绝原始乱糟糟的 JSON 换行 */}
                <div className="spec-table" style={{ margin: '14px 0 18px' }}>
                  <div className="spec-row">
                    <span className="spec-label">架构模式</span>
                    <span className="spec-val">
                      {m.kind === 'local_gguf' ? '内置 llama-server (自动拉起)' : 'OpenAI 兼容端点'}
                    </span>
                  </div>

                  {cfg.base_url && (
                    <div className="spec-row">
                      <span className="spec-label">接入地址</span>
                      <span className="spec-val" title={cfg.base_url}>
                        {cfg.base_url}
                      </span>
                    </div>
                  )}

                  <div className="spec-row">
                    <span className="spec-label">模型标识</span>
                    <span className="spec-val">{cfg.model || 'default'}</span>
                  </div>

                  <div className="spec-row">
                    <span className="spec-label">上下文窗口</span>
                    <span className="spec-val">{cfg.ctx_len ? `${cfg.ctx_len.toLocaleString()} tokens` : '4,096 tokens'}</span>
                  </div>

                  {cfg.temperature !== undefined && (
                    <div className="spec-row">
                      <span className="spec-label">采样温度</span>
                      <span className="spec-val">{cfg.temperature}</span>
                    </div>
                  )}

                  {cfg.file_path && (
                    <div className="spec-row">
                      <span className="spec-label">本地文件</span>
                      <span className="spec-val" title={cfg.file_path}>
                        {cfg.file_path}
                      </span>
                    </div>
                  )}

                  {cfg.api_key && (
                    <div className="spec-row">
                      <span className="spec-label">认证密钥</span>
                      <span className="spec-val" style={{ color: '#059669' }}>
                        sk-••••{cfg.api_key.slice(-4)}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* 操作栏底端对齐 */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: 'auto',
                  paddingTop: 12,
                  borderTop: '1px dashed var(--border)'
                }}
              >
                <button
                  className="btn sm"
                  style={{ background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent)', boxShadow: 'none' }}
                  onClick={() => setTestingModel(m)}
                >
                  ⚡ 测试连通性
                </button>

                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
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
          <div className="empty" style={{ gridColumn: '1 / -1', padding: '36px' }}>
            尚未配置模型。请在上方导入本地 .gguf 模型文件或添加本地兼容端点即可开启离线推理。
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
