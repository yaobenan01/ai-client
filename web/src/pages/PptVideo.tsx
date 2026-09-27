import { useState } from 'react'
import { api } from '../lib/api'

export default function PptVideo() {
  const [material, setMaterial] = useState('')
  const [pptx, setPptx] = useState('')
  const [out, setOut] = useState('')
  const [msg, setMsg] = useState('')

  async function genPpt(e: React.FormEvent) {
    e.preventDefault(); setMsg('')
    try {
      await api.createTask({ title: '生成可编辑 PPT', input: `请使用 ppt-master 技能，把以下材料生成可编辑的 PPTX：${material}` })
      setMsg('已创建 PPT 生成任务，请到「任务」页执行并查看产物。')
    } catch (err: any) { setMsg(err.message) }
  }
  async function genVideo(e: React.FormEvent) {
    e.preventDefault(); setMsg('')
    try {
      await api.createTask({ title: 'PPT 转口播视频', input: `请把 PPTX 文件 ${pptx} 转为带本地 TTS 旁白的 MP4 视频，输出到 ${out || 'workspace'}` })
      setMsg('已创建视频任务，请到「任务」页执行并查看产物。')
    } catch (err: any) { setMsg(err.message) }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>PPT / 口播视频</h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>材料 → 原生可编辑 PPTX → 本地 TTS 口播 MP4，全程离线</div>
        </div>
      </div>

      <div className="hero" style={{ marginBottom: 18 }}>
        <div className="pipeline">
          <span className="step">📄 材料</span><span className="arrow">→</span>
          <span className="step">✦ 结构/设计</span><span className="arrow">→</span>
          <span className="step">📊 可编辑 PPTX</span><span className="arrow">→</span>
          <span className="step">🎙 CosyVoice 旁白</span><span className="arrow">→</span>
          <span className="step">🎬 口播 MP4</span>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>✦ 生成可编辑 PPT</h3>
          <form onSubmit={genPpt}>
            <div className="field"><label>材料路径（PDF / DOCX / Markdown / 文本）</label>
              <input className="input" value={material} onChange={(e) => setMaterial(e.target.value)} placeholder="D:\docs\report.pdf" required />
            </div>
            <button className="btn">创建 PPT 任务</button>
          </form>
        </div>

        <div className="card">
          <h3>🎬 PPT → 口播视频</h3>
          <form onSubmit={genVideo}>
            <div className="field"><label>PPTX 文件路径</label>
              <input className="input" value={pptx} onChange={(e) => setPptx(e.target.value)} placeholder="D:\out\deck.pptx" required />
            </div>
            <div className="field"><label>输出目录（可选）</label>
              <input className="input" value={out} onChange={(e) => setOut(e.target.value)} placeholder="D:\out" />
            </div>
            <button className="btn">创建视频任务</button>
          </form>
        </div>
      </div>

      {msg && <p className="muted" style={{ color: 'var(--ok)', marginTop: 14 }}>{msg}</p>}
    </div>
  )
}
