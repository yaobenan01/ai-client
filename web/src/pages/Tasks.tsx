import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

export default function Tasks() {
  const [tasks, setTasks] = useState<any[]>([])
  const [title, setTitle] = useState('')
  const [input, setInput] = useState('')
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => {
    const r = await api.listTasks()
    setTasks(r.tasks)
  }, [])

  useEffect(() => { load().catch(() => {}) }, [load])

  async function create(e: React.FormEvent) {
    e.preventDefault()
    setMsg('')
    try {
      await api.createTask({ title, input })
      setTitle(''); setInput('')
      await load()
    } catch (err: any) { setMsg(err.message) }
  }

  async function run(id: string) {
    await api.runTask(id)
    await load()
  }

  const badge = (s: string) =>
    s === 'done' ? <span className="badge ok">完成</span> :
    s === 'failed' ? <span className="badge err">失败</span> :
    s === 'running' ? <span className="badge warn">运行中</span> :
    s === 'pending' ? <span className="badge">待执行</span> : <span className="badge">{s}</span>

  return (
    <div>
      <h1>任务</h1>
      <div className="card">
        <form onSubmit={create}>
          <div className="field">
            <label>任务标题</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="给任务起个名字" required />
          </div>
          <div className="field">
            <label>任务内容</label>
            <textarea className="input" rows={4} value={input} onChange={(e) => setInput(e.target.value)} placeholder="描述你想让 AI 完成的事情…" required />
          </div>
          <button className="btn">创建任务</button>
          {msg && <p className="muted" style={{ color: 'var(--err)' }}>{msg}</p>}
        </form>
      </div>

      {tasks.map((t) => (
        <div className="card" key={t.id}>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <Link to={`/tasks/${t.id}`}><strong>{t.title}</strong></Link>
            <div className="row">
              {badge(t.status)}
              <button className="btn ghost" onClick={() => run(t.id)}>执行</button>
            </div>
          </div>
          <p className="muted">{t.input.slice(0, 120)}</p>
        </div>
      ))}
      {tasks.length === 0 && <p className="muted">还没有任务。</p>}
    </div>
  )
}
