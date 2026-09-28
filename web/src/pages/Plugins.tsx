import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'

export default function Plugins() {
  const [plugins, setPlugins] = useState<any[]>([])
  const [path, setPath] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.listPlugins()
      setPlugins(r.plugins)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load().catch(() => {})
  }, [load])

  async function install(e: React.FormEvent) {
    e.preventDefault()
    setMsg('')
    try {
      await api.installPlugin(path)
      setPath('')
      await load()
    } catch (err: any) {
      setMsg(err.message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>插件 · 技能生态</h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            兼容 SKILL.md 规范的离线插件运行时，动态注入 Agent 上下文与本地能力
          </div>
        </div>

        <button className="btn ghost sm" onClick={load}>
          {loading ? '刷新中…' : '🔄 重新扫描插件目录'}
        </button>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <h3>✦ 从本地目录离线安装插件</h3>
        <p className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
          指定包含 <code>SKILL.md</code>、执行脚本与依赖说明的本地目录，系统将自动复制登记到离线插件中心。
        </p>
        <form onSubmit={install}>
          <div className="row">
            <div className="field" style={{ flex: 1, marginBottom: 0 }}>
              <input
                className="input"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="包含 SKILL.md 的目录绝对路径，如 D:\plugins\custom-skill"
                required
              />
            </div>
            <button className="btn">安装插件</button>
          </div>
        </form>
        {msg && <p className="muted" style={{ color: 'var(--err)', marginTop: 10 }}>{msg}</p>}
      </div>

      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 14 }}>
        <h3 style={{ margin: 0 }}>已就绪的离线技能 ({plugins.length})</h3>
        <span className="muted" style={{ fontSize: 12 }}>所有启用的技能描述均会自动装配至 Agent 系统提示词</span>
      </div>

      <div className="grid">
        {plugins.map((p) => (
          <div className="card" key={p.id}>
            <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
              <strong style={{ fontSize: 16 }}>✦ {p.name}</strong>
              <span className="badge done">
                <i className="dot" />
                {p.enabled ? '已启用 (Active)' : '已停用'}
              </span>
            </div>
            <p className="muted" style={{ margin: 0, lineHeight: 1.6, minHeight: 48, fontSize: 13 }}>
              {p.description || '（该插件未提供详细说明描述）'}
            </p>
            <div className="kv" style={{ marginTop: 12 }}>
              <span>插件 ID</span>
              <span className="mono">{p.id}</span>
            </div>
            <div className="kv">
              <span>磁盘路径</span>
              <span className="mono" style={{ overflowWrap: 'anywhere', maxWidth: 220, textAlign: 'right', fontSize: 11 }}>
                {p.path}
              </span>
            </div>
          </div>
        ))}
        {plugins.length === 0 && (
          <div className="empty" style={{ gridColumn: '1 / -1' }}>
            暂无插件。内置 ppt-master 插件随应用自带，或在上方安装新插件。
          </div>
        )}
      </div>
    </div>
  )
}
