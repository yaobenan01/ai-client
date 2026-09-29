import { useState } from 'react'
import { api } from '../lib/api'

interface ModelTestModalProps {
  model: { id: string; name: string; kind: string }
  onClose: () => void
}

export default function ModelTestModal({ model, onClose }: ModelTestModalProps) {
  const [prompt, setPrompt] = useState('你好！请用一句话自我介绍并确认模型已离线就绪。')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [err, setErr] = useState('')

  async function handleTest(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setErr('')
    setResult(null)
    try {
      const res = await api.testModel(model.id, prompt)
      setResult(res)
    } catch (e: any) {
      setErr(e.message || '测试失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>模型连通性与响应测试</h3>
            <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>
              当前测试：<strong>{model.name}</strong> <span className="mono">({model.kind})</span>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleTest}>
          <div className="field" style={{ marginTop: 14 }}>
            <label>测试 Prompt</label>
            <input
              className="input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="输入测试提示词…"
              required
            />
          </div>

          <div className="row" style={{ justifyContent: 'flex-end', marginTop: 10 }}>
            <button type="button" className="btn ghost sm" onClick={onClose}>
              关闭
            </button>
            <button className="btn sm" disabled={loading || !prompt.trim()}>
              {loading ? '测速与推理中…' : '⚡ 发起探针测试'}
            </button>
          </div>
        </form>

        {loading && (
          <div className="test-loading">
            <div className="thinking">
              <i />
              <i />
              <i />
            </div>
            <span>正在连接本地端点并测量延迟…</span>
          </div>
        )}

        {err && (
          <div className="test-error-box">
            <strong>❌ 连接异常</strong>
            <p style={{ margin: '4px 0 8px' }}>{err}</p>
            {(err.includes('llama-server') || err.includes('program not found')) && (
              <div style={{ marginTop: 8, padding: '8px 10px', background: 'rgba(239, 68, 68, 0.08)', borderRadius: 6, fontSize: 12, lineHeight: 1.6 }}>
                <div><strong>💡 诊断排查建议：</strong></div>
                <div>1. 纯本地 GGUF 模型需由 <code>llama-server.exe</code> 加载。已自动下载至 <code>sidecars/llama.cpp/</code> 与 AppData。</div>
                <div>2. 若已有运行中的 Ollama (端口 11434)、LM Studio (1234) 或 vLLM，可在「大模型」中添加为 <strong>OpenAI 兼容端点</strong>，无需重复拉起子进程。</div>
              </div>
            )}
          </div>
        )}

        {result && (
          <div className="test-result-box">
            <div className="test-metrics">
              <span className="badge done">
                <i className="dot" />
                连通成功
              </span>
              <span className="metric-pill">
                端到端延迟: <strong>{result.latency_ms} ms</strong>
              </span>
              <span className="metric-pill">结束状态: {result.finish_reason}</span>
            </div>

            <div className="test-response">
              <div className="response-label">模型实际回答：</div>
              <div className="response-body">{result.response || '（返回内容为空）'}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
