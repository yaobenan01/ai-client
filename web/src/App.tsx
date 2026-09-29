import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './store/auth'
import { waitForCore } from './lib/api'
import Login from './pages/Login'
import Models from './pages/Models'
import Tasks from './pages/Tasks'
import TaskDetail from './pages/TaskDetail'
import Plugins from './pages/Plugins'
import PptVideo from './pages/PptVideo'

const Icon = ({ d }: { d: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
)

const NAV = [
  { to: '/tasks', label: '任务', d: 'M12 3v3M5.6 5.6l2.1 2.1M3 12h3M5.6 18.4l2.1-2.1M12 21v-3M18.4 18.4l-2.1-2.1M21 12h-3M18.4 5.6l-2.1 2.1' },
  { to: '/models', label: '大模型', d: 'M9 3h6M9 3v3h6V3M12 6v4M7 21h10M7 21a3 3 0 0 1-3-3v-3M17 21a3 3 0 0 0 3-3v-3M7 15h10M7 15v-3h10v3' },
  { to: '/plugins', label: '插件', d: 'M10 3.5a2 2 0 0 1 4 0V5h1a2 2 0 0 1 2 2v1h1.5a2 2 0 0 1 0 4H17v1a2 2 0 0 1-2 2h-1v1.5a2 2 0 0 1-4 0V16h-1a2 2 0 0 1-2-2v-1H5.5a2 2 0 0 1 0-4H7V7a2 2 0 0 1 2-2h1V3.5z' },
  { to: '/ppt', label: 'PPT / 视频', d: 'M4 4h16v12H4zM4 16l4-4 3 3 4-4 5 5M9 8h.01M12 8h.01M15 8h.01' }
]

function Logo({ size = 34 }: { size?: number }) {
  return (
    <span className="logo" style={{ width: size, height: size }}>
      <svg viewBox="0 0 24 24" width={size * 0.6} height={size * 0.6} fill="currentColor">
        <path d="M12 2l2.1 6.4L20 11l-5.9 2.6L12 20l-2.1-6.4L4 11l5.9-2.6L12 2z" />
      </svg>
    </span>
  )
}

type CoreState = 'starting' | 'ready' | 'failed'

/** 冷启动时 core 还没监听端口，用友好提示替代空白/报错窗口。 */
function BootScreen({ failed, onRetry }: { failed?: boolean; onRetry?: () => void }) {
  return (
    <div className="login-wrap">
      <div className="card" style={{ width: 430, textAlign: 'center', padding: '34px 28px' }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 14 }}>
          <Logo size={46} />
        </div>
        <h3 style={{ marginBottom: 8 }}>
          {failed ? '本地核心服务启动失败' : '正在启动本地 AI 引擎'}
        </h3>
        <p className="muted" style={{ fontSize: 13, lineHeight: 1.7, margin: 0 }}>
          {failed
            ? '核心引擎未能就绪。请查看日志 %APPDATA%\\com.local.aiclient\\ai-client\\core.log 后重试。'
            : '正在拉起内置执行引擎，首次启动可能需要几秒…'}
        </p>
        {!failed && (
          <div className="thinking" style={{ marginTop: 18 }}><i /><i /><i /></div>
        )}
        {failed && onRetry && (
          <button className="btn" style={{ marginTop: 18 }} onClick={onRetry}>重新尝试</button>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const { user, loading, refresh, logout } = useAuth()
  const [core, setCore] = useState<CoreState>('starting')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let alive = true
    setCore('starting')
    waitForCore(30000).then((ok) => {
      if (!alive) return
      if (ok) {
        setCore('ready')
        refresh()
      } else {
        setCore('failed')
      }
    })
    return () => { alive = false }
  }, [refresh, attempt])

  if (core === 'failed') {
    return <BootScreen failed onRetry={() => setAttempt((n) => n + 1)} />
  }
  if (core === 'starting') return <BootScreen />

  if (loading) {
    return (
      <div className="login-wrap">
        <div className="thinking"><i /><i /><i /></div>
      </div>
    )
  }
  if (!user) return <Login />

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><Logo /><b>AI 客户端</b></div>
        <nav className="nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              <Icon d={n.d} /><span>{n.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="avatar">{user.username.slice(0, 1).toUpperCase()}</span>
          <div className="uname-wrap">
            <div className="uname">{user.username}</div>
            <button className="logout" onClick={logout}>退出登录</button>
          </div>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/tasks" replace />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/tasks/:id" element={<TaskDetail />} />
          <Route path="/models" element={<Models />} />
          <Route path="/plugins" element={<Plugins />} />
          <Route path="/ppt" element={<PptVideo />} />
        </Routes>
      </main>
    </div>
  )
}

