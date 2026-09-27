import { useEffect } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './store/auth'
import Login from './pages/Login'
import Models from './pages/Models'
import Tasks from './pages/Tasks'
import TaskDetail from './pages/TaskDetail'
import Plugins from './pages/Plugins'
import PptVideo from './pages/PptVideo'

export default function App() {
  const { user, loading, refresh, logout } = useAuth()

  useEffect(() => { refresh() }, [refresh])

  if (loading) return <div className="login-wrap muted">加载中…</div>
  if (!user) return <Login />

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">离线 AI 智能体</div>
        <NavLink to="/tasks" className={({ isActive }) => (isActive ? 'active' : '')}>任务</NavLink>
        <NavLink to="/models" className={({ isActive }) => (isActive ? 'active' : '')}>大模型</NavLink>
        <NavLink to="/plugins" className={({ isActive }) => (isActive ? 'active' : '')}>插件</NavLink>
        <NavLink to="/ppt" className={({ isActive }) => (isActive ? 'active' : '')}>PPT / 视频</NavLink>
        <div style={{ flex: 1 }} />
        <div className="muted" style={{ padding: '8px 12px' }}>{user.username}</div>
        <button className="btn ghost" onClick={logout}>退出登录</button>
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
