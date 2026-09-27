import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../lib/api'

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const [task, setTask] = useState<any>(null)
  const [err, setErr] = useState('')

  async function load() {
    try {
      const r = await api.getTask(id!)
      setTask(r.task)
      setErr('')
    } catch (e: any) { setErr(e.message) }
  }

  async function run() { await api.runTask(id!); await load() }

  useEffect(() => {
    load()
    const t = setInterval(() => {
      if (task && (task.status === 'running' || task.status === 'pending')) load()
    }, 2000)
    return () => clearInterval(t)
  }, [id, task?.status])

  if (err) return <p style={{ color: 'var(--err)' }}>{err}</p>
  if (!task) return <p className="muted">加载中…</p>

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>{task.title}</h1>
        <div className="row">
          <span className="badge">{task.status}</span>
          <button className="btn" onClick={run}>执行</button>
        </div>
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>任务内容</h3>
        <pre className="log">{task.input}</pre>
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>执行结果</h3>
        <pre className="log">{task.result || '（暂无结果）'}</pre>
      </div>
    </div>
  )
}
