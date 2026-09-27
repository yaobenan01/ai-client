import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'

export default function Plugins() {
  const [plugins, setPlugins] = useState<any[]>([])
  const [path, setPath] = useState('')
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => {
    const r = await api.listPlugins()
    setPlugins(r.plugins)
  }, [])

  useEffect(() => { load().catch(() => {}) }, [load])

  async function install(e: React.FormEvent) {
    e.preventDefault()
    setMsg('')
    try {
      await api.installPlugin(path)
      setPath('')
      await load()
    } catch (err: any) { setMsg(err.message) }
  }

  return (
    <div>
      <h1>插件 / 技能</h1>
      <div className="card">
        <form onSubmit={install}>
          <div className="field">
            <label>从本地目录安装（需包含 SKILL.md）</label>
            <input className="input" value={path} onChange={(e) => setPath(e.target.value)} placeholder="D:\...\ppt-master" />
          </div>
          <button className="btn">安装</button>
          {msg && <p className="muted" style={{ color: 'var(--err)' }}>{msg}</p>}
        </form>
      </div>

      <div className="grid">
        {plugins.map((p) => (
          <div className="card" key={p.id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>{p.name}</strong>
              <span className="badge ok">{p.enabled ? '启用' : '停用'}</span>
            </div>
            <p className="muted">{p.description}</p>
            <p className="muted mono" style={{ fontSize: 12 }}>{p.path}</p>
          </div>
        ))}
        {plugins.length === 0 && <p className="muted">暂无插件。内置的 ppt-master 会在插件目录就绪后出现在这里。</p>}
      </div>
    </div>
  )
}
