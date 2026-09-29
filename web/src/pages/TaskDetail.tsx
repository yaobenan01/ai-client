import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import ProgressBar from '../components/ProgressBar'
import LogViewer from '../components/LogViewer'
import ArtifactCard from '../components/ArtifactCard'

const BADGE: Record<string, string> = {
  done: 'done',
  failed: 'failed',
  running: 'running',
  pending: 'pending',
  planning: 'planning',
  cancelled: 'failed',
}

const BADGE_TEXT: Record<string, string> = {
  done: '执行成功',
  failed: '执行失败',
  running: '正在执行',
  pending: '等待就绪',
  planning: '规划中',
  cancelled: '已取消',
}

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const [task, setTask] = useState<any>(null)
  const [err, setErr] = useState('')
  const [actionMsg, setActionMsg] = useState('')
  const [copied, setCopied] = useState(false)

  async function load() {
    try {
      const r = await api.getTask(id!)
      setTask(r.task)
      setErr('')
    } catch (e: any) {
      setErr(e.message)
    }
  }

  async function run() {
    setActionMsg('')
    try {
      await api.runTask(id!)
      await load()
    } catch (e: any) {
      setActionMsg(e.message)
    }
  }

  async function cancel() {
    if (!confirm('确定要停止当前正在执行的任务吗？')) return
    setActionMsg('')
    try {
      await api.cancelTask(id!)
      await load()
    } catch (e: any) {
      setActionMsg(e.message)
    }
  }

  async function remove() {
    if (!confirm('确定删除该任务记录吗？')) return
    try {
      await api.deleteTask(id!)
      nav('/tasks')
    } catch (e: any) {
      setActionMsg(e.message)
    }
  }

  function copyResult() {
    if (!task?.result) return
    navigator.clipboard.writeText(task.result)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  useEffect(() => {
    load()
    const t = setInterval(() => {
      if (task && ['running', 'pending', 'planning'].includes(task.status)) {
        load()
      }
    }, 1200)
    return () => clearInterval(t)
  }, [id, task?.status])

  if (err) return <p style={{ color: 'var(--err)' }}>{err}</p>
  if (!task) {
    return (
      <div className="login-wrap">
        <div className="thinking">
          <i />
          <i />
          <i />
        </div>
      </div>
    )
  }

  const running = ['running', 'pending', 'planning'].includes(task.status)

  let artifactsList: string[] = []
  try {
    if (task.artifacts) {
      artifactsList = typeof task.artifacts === 'string' ? JSON.parse(task.artifacts) : task.artifacts
    }
  } catch {}

  const createdTime = task.created_at ? new Date(task.created_at * 1000).toLocaleString() : ''
  const updatedTime = task.updated_at ? new Date(task.updated_at * 1000).toLocaleString() : ''

  return (
    <div style={{ maxWidth: 1040, margin: '0 auto' }}>
      <div className="page-head">
        <div className="row" style={{ gap: 12 }}>
          <Link to="/tasks" className="btn ghost sm">
            ← 返回列表
          </Link>
          <h1 style={{ margin: 0 }}>{task.title}</h1>
          <span className={`badge ${BADGE[task.status] || 'pending'}`}>
            <i className="dot" />
            {BADGE_TEXT[task.status] || task.status}
          </span>
        </div>

        <div className="row" style={{ gap: 8 }}>
          {running ? (
            <button className="btn danger sm" onClick={cancel}>
              🛑 停止任务
            </button>
          ) : (
            <button className="btn sm" onClick={run}>
              ✦ 重新执行
            </button>
          )}
          <button className="btn ghost sm" onClick={remove} title="删除任务">
            🗑
          </button>
        </div>
      </div>

      {actionMsg && <div className="test-error-box" style={{ marginBottom: 16 }}>{actionMsg}</div>}

      {/* 进度控制条 */}
      <div className="card" style={{ marginBottom: 18, padding: 18 }}>
        <ProgressBar progress={task.progress || (task.status === 'done' ? 100 : 0)} status={task.status} />

        <div className="row" style={{ marginTop: 14, justifyContent: 'space-between', fontSize: 12, color: 'var(--muted)' }}>
          <span>任务 ID: <code className="mono">{task.id}</code></span>
          <span>创建时间: {createdTime}</span>
          {updatedTime && <span>更新时间: {updatedTime}</span>}
        </div>
      </div>

      {/* 目标输入卡片 */}
      <div className="card" style={{ marginBottom: 18 }}>
        <h3 style={{ fontSize: 14, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          任务指令与输入
        </h3>
        <div style={{ fontSize: 15, lineHeight: 1.7, background: 'var(--bg-2)', padding: '14px 16px', borderRadius: 10 }}>
          {task.input}
        </div>
      </div>

      {/* 最终结果卡片 */}
      <div className="card" style={{ marginBottom: 18, borderLeft: '4px solid var(--accent)' }}>
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>✦ 执行结论</span>
            {running && <span className="thinking" style={{ transform: 'scale(0.8)' }}><i /><i /><i /></span>}
          </h3>
          {task.result && (
            <button className="btn ghost sm" onClick={copyResult}>
              {copied ? '✓ 已复制结论' : '复制结果'}
            </button>
          )}
        </div>

        <div className="result-content" style={{ fontSize: 14, lineHeight: 1.8, minHeight: 60 }}>
          {running && !task.result ? (
            <div className="muted" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0' }}>
              <span className="thinking"><i /><i /><i /></span>
              Agent 正在拆解目标、调用内置工具与插件运行时处理中…
            </div>
          ) : task.result ? (
            <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {task.result}
            </div>
          ) : (
            <div className="muted">尚未生成结果，请点击右上角「重新执行」启动任务。</div>
          )}
        </div>
      </div>

      {/* 产物交付列表 */}
      {artifactsList.length > 0 && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>📦 交付产物 ({artifactsList.length})</h3>
            <span className="muted" style={{ fontSize: 12 }}>可打开文件 / 定位目录 / 下载 / 复制路径</span>
          </div>
          <div className="grid">
            {artifactsList.map((item, idx) => (
              <ArtifactCard key={idx} path={item} />
            ))}
          </div>
        </div>
      )}

      {/* 规划与执行轨迹时间线 */}
      <div className="card">
        <h3 style={{ marginBottom: 14 }}>🔍 规划与执行轨迹</h3>
        <LogViewer logsJson={task.logs} />
      </div>
    </div>
  )
}
