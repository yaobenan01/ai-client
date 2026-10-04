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
  const [offlineActionRunning, setOfflineActionRunning] = useState(false)

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

  // 离线免 API 直接生成 PPT
  async function handleQuickOfflinePpt() {
    if (!task?.input) return
    setOfflineActionRunning(true)
    setActionMsg('正在调用本地离线引擎直接生成多版式 PPTX...')
    try {
      const res = await api.quickGeneratePpt({ content: task.input })
      setActionMsg(`✓ 离线 PPTX 生成成功！已交付至: ${res.filename || res.path}`)
      await load()
    } catch (e: any) {
      setActionMsg(`离线生成失败: ${e.message}`)
    } finally {
      setOfflineActionRunning(false)
    }
  }

  // 离线免 API 将已有 PPT 转为口播视频
  async function handleQuickOfflineVideo(pptxPath: string) {
    setOfflineActionRunning(true)
    setActionMsg('正在调用内置全离线流水线（LibreOffice + Piper + FFmpeg）渲染口播视频...')
    try {
      const res = await api.quickRenderVideo({ pptx_path: pptxPath })
      setActionMsg(`✓ 口播视频渲染成功！成片: ${res.filename || res.path}`)
      await load()
    } catch (e: any) {
      setActionMsg(`口播视频渲染失败: ${e.message}`)
    } finally {
      setOfflineActionRunning(false)
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(() => {
      if (task && ['running', 'pending', 'planning'].includes(task.status)) {
        load()
      }
    }, 1500)
    return () => clearInterval(t)
  }, [id, task?.status])

  if (err) return <div className="card"><div className="test-error-box">{err}</div></div>
  if (!task) return <div className="card"><span className="muted">正在加载任务详情…</span></div>

  const running = ['running', 'pending', 'planning'].includes(task.status)
  const isFailed = task.status === 'failed'
  const isBalanceError = isFailed && (
    task.result?.includes('402') ||
    task.result?.includes('余额不足') ||
    task.result?.includes('Insufficient Balance')
  )
  const isAuthError = isFailed && (
    task.result?.includes('401') ||
    task.result?.includes('未授权') ||
    task.result?.includes('Unauthorized')
  )

  let artifactsList: string[] = []
  try {
    if (task.artifacts) {
      artifactsList = typeof task.artifacts === 'string' ? JSON.parse(task.artifacts) : task.artifacts
    }
  } catch {
    artifactsList = []
  }

  // 找到已生成的 PPTX 文件
  const existingPptx = artifactsList.find((f) => f.toLowerCase().endsWith('.pptx'))

  const createdTime = task.created_at ? new Date(task.created_at * 1000).toLocaleString() : '-'
  const updatedTime = task.updated_at ? new Date(task.updated_at * 1000).toLocaleString() : ''

  return (
    <div>
      {/* 头部标题与控制按钮 */}
      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 18, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Link to="/tasks" style={{ fontSize: 13, color: 'var(--muted)', display: 'inline-block', marginBottom: 6 }}>
            ← 返回任务列表
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <h2 style={{ margin: 0 }}>{task.title || '无标题任务'}</h2>
            <span className={`badge ${BADGE[task.status] || ''}`}>
              {BADGE_TEXT[task.status] || task.status}
            </span>
          </div>
        </div>

        <div className="row" style={{ gap: 8 }}>
          {running ? (
            <button className="btn ghost sm danger" onClick={cancel}>
              停止执行
            </button>
          ) : (
            <button className="btn primary sm" onClick={run} title="重新使用当前配置启动执行">
              ▶ 重新执行
            </button>
          )}
          <button className="btn ghost sm" onClick={remove} title="删除任务">
            🗑
          </button>
        </div>
      </div>

      {actionMsg && <div className="test-error-box" style={{ marginBottom: 16 }}>{actionMsg}</div>}

      {/* 任务失败与大模型余额耗尽诊断引导卡片 */}
      {isBalanceError && (
        <div
          className="card"
          style={{
            marginBottom: 18,
            border: '1px solid rgba(239, 68, 68, 0.4)',
            background: 'rgba(239, 68, 68, 0.05)',
            padding: '16px 20px',
            borderRadius: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span style={{ fontSize: 22 }}>⚠️</span>
            <strong style={{ fontSize: 16, color: '#ef4444' }}>
              在线大模型 API 余额耗尽 (HTTP 402 Payment Required)
            </strong>
          </div>
          <p style={{ margin: '0 0 14px 0', fontSize: 13.5, color: 'var(--text-1)', lineHeight: 1.6 }}>
            您当前配置的在线大模型服务商账户额度已耗尽，导致 Agent 无法调用云端接口。您可以通过以下途径快速解决：
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <button className="btn primary sm" onClick={() => nav('/settings')}>
              ⚙️ 前往设置中心更换 API Key / 切换模型
            </button>
            <button
              className="btn sm"
              style={{ background: 'var(--accent, #4f46e5)', color: '#fff' }}
              onClick={handleQuickOfflinePpt}
              disabled={offlineActionRunning}
            >
              {offlineActionRunning ? '正在处理...' : '⚡ 使用内置离线引擎直接生成 PPT (免 API 额度)'}
            </button>
            <button className="btn ghost sm" onClick={run}>
              🔄 充值后重新执行任务
            </button>
          </div>
        </div>
      )}

      {isAuthError && (
        <div
          className="card"
          style={{
            marginBottom: 18,
            border: '1px solid rgba(245, 158, 11, 0.4)',
            background: 'rgba(245, 158, 11, 0.05)',
            padding: '16px 20px',
            borderRadius: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span style={{ fontSize: 22 }}>🔑</span>
            <strong style={{ fontSize: 16, color: '#f59e0b' }}>
              API 密钥未授权或无效 (HTTP 401 Unauthorized)
            </strong>
          </div>
          <p style={{ margin: '0 0 12px 0', fontSize: 13.5, color: 'var(--text-1)' }}>
            请检查当前使用的 API Key 是否填写正确、已启用或存在过期情况。
          </p>
          <button className="btn primary sm" onClick={() => nav('/settings')}>
            前往设置中心检查密钥
          </button>
        </div>
      )}

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
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: 10 }}>
          <h3 style={{ margin: 0, fontSize: 14, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            任务指令与输入
          </h3>
          <button
            className="btn ghost sm"
            style={{ fontSize: 12 }}
            onClick={handleQuickOfflinePpt}
            disabled={offlineActionRunning}
            title="无需消耗大模型 API 额度，直接基于输入生成 PPT"
          >
            ⚡ 离线直出 PPT
          </button>
        </div>
        <div style={{ fontSize: 15, lineHeight: 1.7, background: 'var(--bg-2)', padding: '14px 16px', borderRadius: 10 }}>
          {task.input}
        </div>
      </div>

      {/* 最终结果卡片 */}
      <div
        className="card"
        style={{
          marginBottom: 18,
          borderLeft: isFailed ? '4px solid var(--red, #ef4444)' : '4px solid var(--accent)',
        }}
      >
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
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
            <h3 style={{ margin: 0 }}>📦 交付产物 ({artifactsList.length})</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {existingPptx && (
                <button
                  className="btn sm primary"
                  onClick={() => handleQuickOfflineVideo(existingPptx)}
                  disabled={offlineActionRunning}
                  style={{ fontSize: 12 }}
                >
                  🎬 一键将此 PPT 转为口播视频
                </button>
              )}
              <span className="muted" style={{ fontSize: 12 }}>可打开文件 / 定位目录 / 下载</span>
            </div>
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
        <LogViewer logsJson={task.logs} running={task.status === "running" || task.status === "planning"} />
      </div>
    </div>
  )
}
