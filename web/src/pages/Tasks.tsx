import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

const BADGE: Record<string, string> = {
  done: 'done', failed: 'failed', running: 'running', pending: 'pending', planning: 'planning'
}
const BADGE_TEXT: Record<string, string> = {
  done: '完成', failed: '失败', running: '执行中', pending: '待执行', planning: '规划中'
}

export default function Tasks() {
  const nav = useNavigate()
  const [tasks, setTasks] = useState<any[]>([])
  const [title, setTitle] = useState('')
  const [input, setInput] = useState('')
  const [msg, setMsg] = useState('')
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    const r = await api.listTasks()
    setTasks(r.tasks)
  }, [])

  useEffect(() => { load().catch(() => {}) }, [load])

  async function create(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim()) return
    setCreating(true); setMsg('')
    try {
      const r = await api.createTask({ title: title.trim() || input.trim().slice(0, 24), input })
      setTitle(''); setInput('')
      await load()
      nav(`/tasks/${r.task.id}`)
    } catch (err: any) { setMsg(err.message) } finally { setCreating(false) }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>任务</h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>给 AI 一个目标，它来规划、执行并交付结果</div>
        </div>
        <span className="badge pending"><i className="dot" />本地 Agent</span>
      </div>

      <div className="hero" style={{ marginBottom: 20 }}>
        <form onSubmit={create}>
          <div className="field" style={{ marginBottom: 10 }}>
            <label>任务目标</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="给任务起个名字（可选）" />
          </div>
          <div className="field" style={{ marginBottom: 14 }}>
            <label>任务内容</label>
            <textarea className="input" rows={3} value={input} onChange={(e) => setInput(e.target.value)}
              placeholder="例如：把 D:\docs\report.pdf 做成一份 8 页的可编辑 PPT，并导出带口播的视频…" />
          </div>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <span className="muted" style={{ fontSize: 12 }}>支持自然语言描述，AI 会自动规划执行步骤</span>
            <button className="btn" disabled={creating || !input.trim()}>{creating ? '创建中…' : '✦ 开始执行'}</button>
          </div>
          {msg && <p className="muted" style={{ color: 'var(--err)', marginTop: 10 }}>{msg}</p>}
        </form>
      </div>

      {tasks.length === 0 ? (
        <div className="empty">还没有任务，在上面创建第一个任务吧 ✦</div>
      ) : (
        <div className="grid">
          {tasks.map((t) => (
            <div className="card" key={t.id} style={{ cursor: 'pointer' }} onClick={() => nav(`/tasks/${t.id}`)}>
              <div className="row" style={{ justifyContent: 'space-between', marginBottom: 10 }}>
                <strong style={{ fontSize: 15 }}>{t.title}</strong>
                <span className={`badge ${BADGE[t.status] || 'pending'}`}><i className="dot" />{BADGE_TEXT[t.status] || t.status}</span>
              </div>
              <p className="muted" style={{ margin: 0, lineHeight: 1.6, minHeight: 44 }}>{t.input.slice(0, 110)}</p>
              <div className="row" style={{ marginTop: 12, justifyContent: 'flex-end' }}>
                <span className="muted" style={{ fontSize: 12 }}>查看执行 →</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
