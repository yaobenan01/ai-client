import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import ProgressBar from '../components/ProgressBar'

const BADGE: Record<string, string> = {
  done: 'done',
  failed: 'failed',
  running: 'running',
  pending: 'pending',
  planning: 'planning',
  cancelled: 'failed',
}
const BADGE_TEXT: Record<string, string> = {
  done: '完成',
  failed: '失败',
  running: '执行中',
  pending: '待执行',
  planning: '规划中',
  cancelled: '已取消',
}

const TEMPLATES = [
  {
    title: '📄 报告转可编辑 PPT',
    prompt: '请使用内置 ppt-master 插件，将工作区或指定文档中的核心内容，提炼为一份 8 页结构严密的原生可编辑 PPTX 演示文稿。',
  },
  {
    title: '🎬 PPTX 转口播视频',
    prompt: '请把指定的 PPTX 演示文稿转为带离线 TTS 演讲者旁白的口播 MP4 视频，输出至 exports 目录。',
  },
  {
    title: '🔍 本地文档归纳与分析',
    prompt: '请读取工作区内相关文档，整理核心逻辑框架、关键数据指标，并输出结构化总结报告。',
  },
  {
    title: '✍️ 业务实施方案拟定',
    prompt: '请根据离线客户端的产品定位与交付要求，拟定一份清晰的落地执行计划与技术攻坚路线。',
  },
]

export default function Tasks() {
  const nav = useNavigate()
  const [tasks, setTasks] = useState<any[]>([])
  const [models, setModels] = useState<any[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [title, setTitle] = useState('')
  const [input, setInput] = useState('')
  const [filter, setFilter] = useState<'all' | 'running' | 'done' | 'failed'>('all')
  const [msg, setMsg] = useState('')
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    const [taskRes, modelRes] = await Promise.all([api.listTasks(), api.listModels().catch(() => ({ models: [], default: null }))])
    setTasks(taskRes.tasks)
    setModels(modelRes.models)
    if (modelRes.default) setSelectedModel(modelRes.default)
    else if (modelRes.models.length > 0) setSelectedModel(modelRes.models[0].id)
  }, [])

  useEffect(() => {
    load().catch(() => {})
  }, [load])

  async function create(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim()) return
    setCreating(true)
    setMsg('')
    try {
      const r = await api.createTask({
        title: title.trim() || input.trim().slice(0, 24),
        input,
        model_id: selectedModel || undefined,
      })
      setTitle('')
      setInput('')
      await api.runTask(r.task.id).catch(() => {})
      await load()
      nav(`/tasks/${r.task.id}`)
    } catch (err: any) {
      setMsg(err.message)
    } finally {
      setCreating(false)
    }
  }

  async function deleteTask(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    if (!confirm('确认删除该任务记录吗？')) return
    try {
      await api.deleteTask(id)
      await load()
    } catch (err: any) {
      alert(err.message)
    }
  }

  function applyTemplate(tpl: typeof TEMPLATES[0]) {
    setTitle(tpl.title.replace(/^[^\s]+\s/, ''))
    setInput(tpl.prompt)
  }

  const filteredTasks = tasks.filter((t) => {
    if (filter === 'all') return true
    if (filter === 'running') return ['running', 'pending', 'planning'].includes(t.status)
    if (filter === 'done') return t.status === 'done'
    if (filter === 'failed') return t.status === 'failed' || t.status === 'cancelled'
    return true
  })

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>任务看板</h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            自然语言驱动的本地 Agent，自主规划、工具调度与交付
          </div>
        </div>
        <div className="row">
          <span className="badge pending">
            <i className="dot" />
            全离线沙箱执行
          </span>
        </div>
      </div>

      {/* 创建任务卡片 */}
      <div className="hero" style={{ marginBottom: 20 }}>
        <form onSubmit={create}>
          <div className="row" style={{ marginBottom: 12, gap: 12 }}>
            <div className="field" style={{ flex: 2, marginBottom: 0 }}>
              <label>任务目标 / 标题</label>
              <input
                className="input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="简明扼要的目标标题（可选）"
              />
            </div>

            <div className="field" style={{ flex: 1, minWidth: 200, marginBottom: 0 }}>
              <label>执行模型</label>
              <select
                className="input"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                <option value="">跟随全局默认模型</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.kind})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="field" style={{ marginBottom: 12 }}>
            <label>任务详细要求（支持自然语言规划）</label>
            <textarea
              className="input"
              rows={3}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="例如：把 D:\docs\report.md 提炼为 8 页可编辑 PPTX，并用本地 CosyVoice 合成口播视频…"
              required
            />
          </div>

          {/* 模版快捷选择 */}
          <div className="template-pills">
            <span className="template-label">快捷场景：</span>
            {TEMPLATES.map((tpl, i) => (
              <button
                type="button"
                key={i}
                className="template-pill"
                onClick={() => applyTemplate(tpl)}
              >
                {tpl.title}
              </button>
            ))}
          </div>

          <div className="row" style={{ justifyContent: 'space-between', marginTop: 14 }}>
            <span className="muted" style={{ fontSize: 12 }}>
              创建后将自动调起 Agent 规划并流式执行
            </span>
            <button className="btn" disabled={creating || !input.trim()}>
              {creating ? '任务创建中…' : '✦ 立即创建并执行'}
            </button>
          </div>
          {msg && <p className="muted" style={{ color: 'var(--err)', marginTop: 10 }}>{msg}</p>}
        </form>
      </div>

      {/* 筛选标签栏 */}
      <div className="tab-bar">
        <button className={`tab-item ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>
          全部任务 ({tasks.length})
        </button>
        <button className={`tab-item ${filter === 'running' ? 'active' : ''}`} onClick={() => setFilter('running')}>
          进行中 ({tasks.filter((t) => ['running', 'pending', 'planning'].includes(t.status)).length})
        </button>
        <button className={`tab-item ${filter === 'done' ? 'active' : ''}`} onClick={() => setFilter('done')}>
          已完成 ({tasks.filter((t) => t.status === 'done').length})
        </button>
        <button className={`tab-item ${filter === 'failed' ? 'active' : ''}`} onClick={() => setFilter('failed')}>
          异常/已停止 ({tasks.filter((t) => t.status === 'failed' || t.status === 'cancelled').length})
        </button>
      </div>

      {/* 任务列表 */}
      {filteredTasks.length === 0 ? (
        <div className="empty">当前分类下暂无任务，可在上方创建新任务 ✦</div>
      ) : (
        <div className="grid">
          {filteredTasks.map((t) => {
            let artCount = 0
            try {
              if (t.artifacts) {
                const arr = typeof t.artifacts === 'string' ? JSON.parse(t.artifacts) : t.artifacts
                artCount = arr.length
              }
            } catch {}

            return (
              <div
                className="card task-card"
                key={t.id}
                onClick={() => nav(`/tasks/${t.id}`)}
              >
                <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
                  <strong style={{ fontSize: 15 }} className="ellipsis-1">
                    {t.title}
                  </strong>
                  <span className={`badge ${BADGE[t.status] || 'pending'}`}>
                    <i className="dot" />
                    {BADGE_TEXT[t.status] || t.status}
                  </span>
                </div>

                <p className="muted task-desc">{t.input}</p>

                <div style={{ margin: '12px 0 6px' }}>
                  <ProgressBar
                    progress={t.progress || (t.status === 'done' ? 100 : 0)}
                    status={t.status}
                    animated={false}
                  />
                </div>

                <div className="row task-card-foot">
                  <div className="row" style={{ gap: 6 }}>
                    {artCount > 0 && (
                      <span className="artifact-badge">
                        📦 {artCount} 个产物
                      </span>
                    )}
                    <span className="muted" style={{ fontSize: 12 }}>
                      {t.created_at ? new Date(t.created_at * 1000).toLocaleDateString() : ''}
                    </span>
                  </div>

                  <div className="row" style={{ gap: 6 }}>
                    <button
                      className="card-del-btn"
                      onClick={(e) => deleteTask(t.id, e)}
                      title="删除任务"
                    >
                      ✕
                    </button>
                    <span className="muted" style={{ fontSize: 12 }}>详情 →</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
