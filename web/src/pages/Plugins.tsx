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
    e.preventDefault(); setMsg('')
    try { await api.installPlugin(path); setPath(''); await load() }
    catch (err: any) { setMsg(err.message) }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>插件 / 技能</h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>以 SKILL.md 为核心的技能运行时，离线安装与执行</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>从本地目录安装</h3>
        <form onSubmit={install}>
          <div className="row">
            <div className="field" style={{ flex: 1, marginBottom: 0 }}>
              <input className="input" value={path} onChange={(e) => setPath(e.target.value)} placeholder="包含 SKILL.md 的目录，如 D:\...\ppt-master" />
            </div>
            <button className="btn">安装</button>
          </div>
        </form>
        {msg && <p className="muted" style={{ color: 'var(--err)', marginTop: 10 }}>{msg}</p>}
      </div>

      <div className="grid">
        {plugins.map((p) => (
          <div className="card" key={p.id}>
            <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
              <strong style={{ fontSize: 15 }}>✦ {p.name}</strong>
              <span className="badge done"><i className="dot" />{p.enabled ? '启用' : '停用'}</span>
            </div>
            <p className="muted" style={{ margin: 0, lineHeight: 1.6, minHeight: 42 }}>{p.description}</p>
            <div className="kv" style={{ marginTop: 8 }}><span>路径</span><span className="mono" style={{ overflowWrap: 'anywhere', maxWidth: 220, textAlign: 'right' }}>{p.path}</span></div>
          </div>
        ))}
        {plugins.length === 0 && <div className="empty" style={{ gridColumn: '1 / -1' }}>暂无插件。内置 ppt-master 会在插件目录就绪后显示在这里。</div>}
      </div>
    </div>
  )
}
