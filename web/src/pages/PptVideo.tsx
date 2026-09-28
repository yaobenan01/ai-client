import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import ArtifactCard from '../components/ArtifactCard'

export default function PptVideo() {
  const nav = useNavigate()
  const [tab, setTab] = useState<'direct' | 'agent'>('direct')

  // Direct fast mode states
  const [pptMode, setPptMode] = useState<'text' | 'file'>('text')
  const [textContent, setTextContent] = useState(
    '# 2026 离线 AI 客户端架构规划\n\n## 核心设计理念\n- 全离线、零联网强制依赖\n- 原生 DrawingML 可编辑 PPTX 渲染\n- 本地 TTS 音画同步口播视频\n- 跨平台支持麒麟、信创与鸿蒙 PWA\n\n## 系统分层架构\n- 核心 Rust 引擎与 Headless HTTP API\n- React + TypeScript 现代化表现层\n- 内嵌 Python + ppt-master 插件体系\n- LibreOffice 与 FFmpeg 视频合成链路\n\n## 下一步计划\n- 附件运行时自动解压与真机适配\n- 端侧小型化模型深度微调与提速\n'
  )
  const [materialPath, setMaterialPath] = useState('')
  const [pptxInput, setPptxInput] = useState('')
  const [ttsEngine, setTtsEngine] = useState('cosyvoice')

  // Loading & status
  const [directLoading, setDirectLoading] = useState(false)
  const [directMsg, setDirectMsg] = useState('')
  const [directError, setDirectError] = useState('')

  // Workspace files list
  const [workspaceFiles, setWorkspaceFiles] = useState<any[]>([])

  const loadFiles = useCallback(async () => {
    try {
      const res = await api.listWorkspaceFiles()
      setWorkspaceFiles(res.files || [])
    } catch {}
  }, [])

  useEffect(() => {
    loadFiles()
  }, [loadFiles])

  // Direct action: Generate PPT
  async function handleDirectPpt(e: React.FormEvent) {
    e.preventDefault()
    setDirectLoading(true)
    setDirectMsg('')
    setDirectError('')
    try {
      const res = await api.quickGeneratePpt(
        pptMode === 'text'
          ? { content: textContent }
          : { input_path: materialPath }
      )
      setDirectMsg(`✓ 成功生成 PPTX：${res.path}`)
      setPptxInput(res.path)
      await loadFiles()
    } catch (e: any) {
      setDirectError(e.message || '生成失败')
    } finally {
      setDirectLoading(false)
    }
  }

  // Direct action: Generate Video
  async function handleDirectVideo(e: React.FormEvent) {
    e.preventDefault()
    if (!pptxInput.trim()) return
    setDirectLoading(true)
    setDirectMsg('')
    setDirectError('')
    try {
      const res = await api.quickRenderVideo({ pptx_path: pptxInput })
      setDirectMsg(`✓ 成功渲染口播视频：${res.path}`)
      await loadFiles()
    } catch (e: any) {
      setDirectError(e.message || '渲染失败')
    } finally {
      setDirectLoading(false)
    }
  }

  // Agent mode: Create agent task
  async function handleAgentPpt(e: React.FormEvent) {
    e.preventDefault()
    try {
      const task = await api.createTask({
        title: 'Agent 制作可编辑 PPT',
        input: `请使用内置 ppt-master 技能与工具，根据材料制作一份原生可编辑 PPTX：${materialPath || textContent}`,
      })
      await api.runTask(task.task.id).catch(() => {})
      nav(`/tasks/${task.task.id}`)
    } catch (e: any) {
      alert(e.message)
    }
  }

  async function handleAgentVideo(e: React.FormEvent) {
    e.preventDefault()
    try {
      const task = await api.createTask({
        title: 'Agent PPT 转口播视频',
        input: `请调用 pptx_to_video 工具，将 PPTX 文件 ${pptxInput} 转为带本地旁白的口播 MP4 视频。`,
      })
      await api.runTask(task.task.id).catch(() => {})
      nav(`/tasks/${task.task.id}`)
    } catch (e: any) {
      alert(e.message)
    }
  }

  const pptFiles = workspaceFiles.filter((f) => ['pptx', 'ppt'].includes(f.ext))
  const videoFiles = workspaceFiles.filter((f) => ['mp4', 'webm'].includes(f.ext))

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>PPT · 口播视频工作台</h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            材料输入 → 原生 DrawingML 可编辑 PPTX → 演讲者旁白 TTS → FFmpeg 口播 MP4，全链路离线交付
          </div>
        </div>

        <div className="row">
          <button className="btn ghost sm" onClick={loadFiles}>
            🔄 刷新产物库
          </button>
        </div>
      </div>

      {/* 视觉工作流流水线 */}
      <div className="hero" style={{ marginBottom: 20 }}>
        <div className="pipeline">
          <span className="step">📄 材料输入 (Markdown/PDF/Docx)</span>
          <span className="arrow">→</span>
          <span className="step">✦ ppt-master 原生排版</span>
          <span className="arrow">→</span>
          <span className="step">📊 原生可编辑 PPTX</span>
          <span className="arrow">→</span>
          <span className="step">🎙 本地 TTS (CosyVoice/Piper)</span>
          <span className="arrow">→</span>
          <span className="step">🎬 FFmpeg 音画口播 MP4</span>
        </div>
      </div>

      {/* 模式切换 */}
      <div className="tab-bar">
        <button
          className={`tab-item ${tab === 'direct' ? 'active' : ''}`}
          onClick={() => setTab('direct')}
        >
          ⚡ 一键快速生成通道 (Direct Mode)
        </button>
        <button
          className={`tab-item ${tab === 'agent' ? 'active' : ''}`}
          onClick={() => setTab('agent')}
        >
          🤖 Agent 智能体规划模式 (Agent Task)
        </button>
      </div>

      {directLoading && (
        <div className="card test-loading" style={{ marginBottom: 18 }}>
          <div className="thinking">
            <i />
            <i />
            <i />
          </div>
          <span>正在调用本地 Python / LibreOffice / FFmpeg 执行处理中，请稍候…</span>
        </div>
      )}

      {directMsg && (
        <div className="card" style={{ marginBottom: 18, borderLeft: '4px solid var(--ok)', color: 'var(--ok)' }}>
          {directMsg}
        </div>
      )}

      {directError && (
        <div className="card test-error-box" style={{ marginBottom: 18 }}>
          <strong>操作失败：</strong> {directError}
        </div>
      )}

      {/* 主工作区 */}
      <div className="grid">
        {/* Step 1: PPT 生成 */}
        <div className="card">
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>✦ 步骤一：生成可编辑 PPTX</h3>
            <span className="badge done">原生 DrawingML</span>
          </div>

          <div className="row" style={{ gap: 6, marginBottom: 14 }}>
            <button
              className={`btn sm ${pptMode === 'text' ? '' : 'ghost'}`}
              onClick={() => setPptMode('text')}
            >
              直接粘贴 Markdown 文本
            </button>
            <button
              className={`btn sm ${pptMode === 'file' ? '' : 'ghost'}`}
              onClick={() => setPptMode('file')}
            >
              指定本地文档路径
            </button>
          </div>

          <form onSubmit={tab === 'direct' ? handleDirectPpt : handleAgentPpt}>
            {pptMode === 'text' ? (
              <div className="field">
                <label>演示大纲与内容（Markdown）</label>
                <textarea
                  className="input mono"
                  rows={8}
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  placeholder="# 演示标题\n\n## 第一页\n- 要点1\n- 要点2"
                  required
                />
              </div>
            ) : (
              <div className="field">
                <label>材料文件路径（PDF / DOCX / Markdown / 文本）</label>
                <input
                  className="input"
                  value={materialPath}
                  onChange={(e) => setMaterialPath(e.target.value)}
                  placeholder="D:\workspace\report.pdf"
                  required
                />
              </div>
            )}

            <button className="btn" disabled={directLoading}>
              {tab === 'direct' ? '⚡ 一键直接生成 PPTX' : '🤖 创建 Agent 深度 PPT 任务'}
            </button>
          </form>
        </div>

        {/* Step 2: 视频渲染 */}
        <div className="card">
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>🎬 步骤二：PPT → 口播视频</h3>
            <span className="badge pending">本地 TTS + FFmpeg</span>
          </div>

          <form onSubmit={tab === 'direct' ? handleDirectVideo : handleAgentVideo}>
            <div className="field">
              <label>PPTX 文件路径（输入或从产物库选择）</label>
              <input
                className="input"
                value={pptxInput}
                onChange={(e) => setPptxInput(e.target.value)}
                placeholder="exports/presentation_2026.pptx"
                required
              />
            </div>

            <div className="field">
              <label>离线 TTS 语音引擎</label>
              <select
                className="input"
                value={ttsEngine}
                onChange={(e) => setTtsEngine(e.target.value)}
              >
                <option value="cosyvoice">CosyVoice（高质量中文旁白，推荐）</option>
                <option value="piper">Piper（轻量级快速模型）</option>
              </select>
            </div>

            <p className="muted" style={{ fontSize: 12, lineHeight: 1.6, margin: '8px 0 16px' }}>
              流水线将自动提取各页的「演讲者备注 (Notes)」，合成对应音频切片，并通过 LibreOffice 转高清 PNG，由 FFmpeg 完成精准对齐合成。
            </p>

            <button className="btn" disabled={directLoading || !pptxInput.trim()}>
              {tab === 'direct' ? '⚡ 启动本地视频渲染' : '🤖 创建 Agent 视频合成任务'}
            </button>
          </form>
        </div>
      </div>

      {/* 工作区产物库 */}
      <div className="card" style={{ marginTop: 24 }}>
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: 14 }}>
          <h3 style={{ margin: 0 }}>📦 工作区已交付产物库 ({workspaceFiles.length})</h3>
          <span className="muted" style={{ fontSize: 12 }}>
            PPT 演示文稿 ({pptFiles.length}) · 口播视频 ({videoFiles.length})
          </span>
        </div>

        {workspaceFiles.length === 0 ? (
          <div className="empty">暂无产物，生成后的 PPTX 与 MP4 将自动出现在这里并支持一键下载。</div>
        ) : (
          <div className="grid">
            {workspaceFiles.map((file, idx) => (
              <ArtifactCard
                key={idx}
                path={file.path}
                name={file.name}
                size={file.size}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
