import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'

const BADGE: Record<string, string> = { done: 'done', failed: 'failed', running: 'running', pending: 'pending', planning: 'planning' }
const BADGE_TEXT: Record<string, string> = { done: '完成', failed: '失败', running: '执行中', pending: '待执行', planning: '规划中' }
const SYSTEM_TEXT: Record<string, string> = {
  pending: '任务已创建，等待执行', planning: '正在规划执行步骤', running: '正在执行任务',
  done: '任务执行完成', failed: '任务执行失败'
}

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const [task, setTask] = useState<any>(null)
  const [err, setErr] = useState('')

  async function load() {
    try {
      const r = await api.getTask(id!)
      setTask(r.task); setErr('')
    } catch (e: any) { setErr(e.message) }
  }
  async function run() { await api.runTask(id!); await load() }

  useEffect(() => {
    load()
    const t = setInterval(() => {
      if (task && ['running', 'pending', 'planning'].includes(task.status)) load()
    }, 2000)
    return () => clearInterval(t)
  }, [id, task?.status])

  if (err) return <p style={{ color: 'var(--err)' }}>{err}</p>
  if (!task) return <div className="thinking"><i /><i /><i /></div>

  const running = ['running', 'pending', 'planning'].includes(task.status)

  return (
    <div>
      <div className="page-head">
        <div className="row">
          <Link to="/tasks" className="btn ghost sm">← 返回</Link>
          <h1>{task.title}</h1>
          <span className={`badge ${BADGE[task.status] || 'pending'}`}><i className="dot" />{BADGE_TEXT[task.status] || task.status}</span>
        </div>
        <button className="btn" onClick={run} disabled={running}>{running ? '执行中…' : '✦ 重新执行'}</button>
      </div>

      <div className="card" style={{ padding: 26 }}>
        <div className="chat">
          <div className="msg system"><div className="bubble">{SYSTEM_TEXT[task.status] || task.status}</div></div>

          <div className="msg user">
            <span className="avatar">你</span>
            <div className="bubble">{task.input}</div>
          </div>

          <div className="msg assistant">
            <span className="avatar">✦</span>
            <div className="bubble">
              {running && !task.result ? (
                <span className="thinking"><i /><i /><i /> Agent 正在工作…</span>
              ) : task.result ? (
                task.result
              ) : (
                <span className="muted">点击右上角「重新执行」开始任务</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
