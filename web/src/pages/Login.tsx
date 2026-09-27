import { useState } from 'react'
import { useAuth } from '../store/auth'

export default function Login() {
  const { login, register, error } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      if (mode === 'login') await login(username, password)
      else await register(username, password)
    } catch {} finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <span className="blob a" />
      <span className="blob b" />
      <span className="blob c" />

      <div className="login-card">
        <div className="login-brand">
          <span className="logo" style={{ width: 54, height: 54 }}>
            <svg viewBox="0 0 24 24" width={32} height={32} fill="currentColor">
              <path d="M12 2l2.1 6.4L20 11l-5.9 2.6L12 20l-2.1-6.4L4 11l5.9-2.6L12 2z" />
            </svg>
          </span>
          <h1>离线 AI 智能体客户端</h1>
          <p>本地登录 · 本地模型 · 任务执行 · 可编辑 PPT 与口播视频</p>
        </div>

        <div className="login-switch">
          <button className={mode === 'login' ? 'on' : ''} onClick={() => setMode('login')}>登录</button>
          <button className={mode === 'register' ? 'on' : ''} onClick={() => setMode('register')}>注册</button>
        </div>

        <form onSubmit={submit}>
          <div className="field">
            <label>用户名</label>
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="输入用户名" autoFocus />
          </div>
          <div className="field">
            <label>密码{mode === 'register' ? '（至少 6 位）' : ''}</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="输入密码" />
          </div>
          {error && <p style={{ color: 'var(--err)', margin: '0 0 12px', fontSize: 13 }}>{error}</p>}
          <button className="btn" style={{ width: '100%', justifyContent: 'center' }} disabled={busy} type="submit">
            {busy ? '请稍候…' : mode === 'login' ? '登录' : '注册并登录'}
          </button>
        </form>
        <p className="muted" style={{ textAlign: 'center', margin: '16px 0 0', fontSize: 12 }}>
          账号与数据均保存在本机，全程离线
        </p>
      </div>
    </div>
  )
}
