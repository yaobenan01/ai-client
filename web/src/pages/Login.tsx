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
    <div className="login-wrap card">
      <h1>本地登录</h1>
      <p className="muted">账号与数据全部保存在本机，全程离线。</p>
      <form onSubmit={submit}>
        <div className="field">
          <label>用户名</label>
          <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </div>
        <div className="field">
          <label>密码（至少 6 位）</label>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p style={{ color: 'var(--err)' }}>{error}</p>}
        <div className="row">
          <button className="btn" disabled={busy} type="submit">{mode === 'login' ? '登录' : '注册并登录'}</button>
          <button className="btn ghost" type="button" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
            {mode === 'login' ? '去注册' : '去登录'}
          </button>
        </div>
      </form>
    </div>
  )
}
