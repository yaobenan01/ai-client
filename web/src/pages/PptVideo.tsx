import { useCallback, useEffect, useRef, useState } from 'react'
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
  const [ttsEngine, setTtsEngine] = useState('auto')
  const [voice, setVoice] = useState('zh-CN-YunxiNeural')
  const [speechRate, setSpeechRate] = useState('+0%')

  // File input refs
  const pptxFileInputRef = useRef<HTMLInputElement>(null)
  const docFileInputRef = useRef<HTMLInputElement>(null)

  // Loading & status
  const [directLoading, setDirectLoading] = useState(false)
  const [directMsg, setDirectMsg] = useState('')
  const [directError, setDirectError] = useState('')
  const [lastResultPath, setLastResultPath] = useState('')
  const [lastResultType, setLastResultType] = useState<'ppt' | 'video' | null>(null)

  // Workspace files list
  const [workspaceFiles, setWorkspaceFiles] = useState<any[]>([])

  const loadFiles = useCallback(async () => {
    try {
      const res = await api.listWorkspaceFiles()
      const files = res.files || []
      setWorkspaceFiles(files)

      // 如果当前尚未填写 PPT 路径，自动取产物库最新的 PPTX 文件作为默认推荐
      const ppts = files.filter((f: any) => ['pptx', 'ppt'].includes(f.ext))
      if (ppts.length > 0) {
        setPptxInput((prev) => (prev ? prev : ppts[0].path))
      }
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
    setLastResultPath('')
    setLastResultType(null)
    try {
      const res = await api.quickGeneratePpt(
        pptMode === 'text'
          ? { content: textContent }
          : { input_path: materialPath }
      )
      setDirectMsg(`✓ 成功生成 PPTX：${res.path}`)
      setLastResultPath(res.path)
      setLastResultType('ppt')
      // 自动同步到步骤二的输入框，形成丝滑连贯的流水线交互
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
    setLastResultPath('')
    setLastResultType(null)
    try {
      const res = await api.quickRenderVideo({
        pptx_path: pptxInput.trim(),
        tts_engine: ttsEngine,
        voice: voice,
        rate: speechRate,
      })
      setDirectMsg(`✓ 成功渲染口播视频：${res.path}`)
      setLastResultPath(res.path)
      setLastResultType('video')
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
        input: `请调用 pptx_to_video 工具，将 PPTX 文件 ${pptxInput} 转为富有感情、生动自然的口播 MP4 视频（音色角色：${voice}，引擎：${ttsEngine}，语速：${speechRate}）。`,
      })
      await api.runTask(task.task.id).catch(() => {})
      nav(`/tasks/${task.task.id}`)
    } catch (e: any) {
      alert(e.message)
    }
  }

  // 本地文件选择回调
  function handlePptxFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      // WebView2 / Electron 中 file 对象暴露原生 local path
      const chosenPath = (file as any).path || file.name
      setPptxInput(chosenPath)
      e.target.value = ''
    }
  }

  function handleDocFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      const chosenPath = (file as any).path || file.name
      setMaterialPath(chosenPath)
      e.target.value = ''
    }
  }

  const pptFiles = workspaceFiles.filter((f) => ['pptx', 'ppt'].includes(f.ext))
  const videoFiles = workspaceFiles.filter((f) => ['mp4', 'webm'].includes(f.ext))

  return (
    <div style={{ maxWidth: 1360, margin: '0 auto' }}>
      {/* 顶部标题区 */}
      <div className="page-head" style={{ marginBottom: 14 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.3px' }}>
            PPT 制作与口播视频工作台
          </h1>
          <div className="muted" style={{ fontSize: 13, marginTop: 5 }}>
            从材料大纲 → 原生 DrawingML 矢量可编辑幻灯片 → 48项备注韵律神经配音 → FFmpeg 音画对齐 MP4 视频
          </div>
        </div>

        <div className="row" style={{ gap: 8 }}>
          <button className="btn ghost sm" onClick={loadFiles} title="刷新工作区产物列表">
            🔄 刷新产物库
          </button>
        </div>
      </div>

      {/* 视觉流程管道 Banner */}
      <div className="hero" style={{ marginBottom: 20, padding: '12px 18px' }}>
        <div className="pipeline" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 12px', alignItems: 'center' }}>
          <span className="step">📄 智能材料输入</span>
          <span className="arrow">→</span>
          <span className="step">✦ DrawingML 矢量排版</span>
          <span className="arrow">→</span>
          <span className="step">📊 原生 PPTX 文稿</span>
          <span className="arrow">→</span>
          <span className="step">🎙️ 宣讲神经语音合成 (云希/晓晓/Piper)</span>
          <span className="arrow">→</span>
          <span className="step">🎬 4K/1080P 口播成片</span>
        </div>
      </div>

      {/* 模式切换 Tab */}
      <div className="tab-bar" style={{ marginBottom: 20 }}>
        <button
          className={`tab-item ${tab === 'direct' ? 'active' : ''}`}
          onClick={() => setTab('direct')}
        >
          ⚡ 一键快速工作台 (Direct Pipeline)
        </button>
        <button
          className={`tab-item ${tab === 'agent' ? 'active' : ''}`}
          onClick={() => setTab('agent')}
        >
          🤖 Agent 自主规划模式 (Agent Task)
        </button>
      </div>

      {/* 运行中状态提示 */}
      {directLoading && (
        <div className="card test-loading" style={{ marginBottom: 20, borderLeft: '4px solid var(--accent)' }}>
          <div className="thinking">
            <i />
            <i />
            <i />
          </div>
          <span style={{ fontSize: 13, fontWeight: 500 }}>
            正在调用本地渲染管线执行处理（LibreOffice 矢量光栅化 / 神经语音合成 / FFmpeg 音视频对齐）…
          </span>
        </div>
      )}

      {/* 成功结果操作条 */}
      {directMsg && (
        <div
          className="card"
          style={{
            marginBottom: 20,
            borderLeft: '4px solid var(--ok)',
            background: 'var(--ok-soft)',
            padding: '14px 18px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12
          }}
        >
          <div style={{ color: 'var(--ok)', fontWeight: 600, fontSize: 13, wordBreak: 'break-all' }}>
            {directMsg}
          </div>
          {lastResultPath && (
            <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
              <button
                type="button"
                className="btn sm"
                style={{ background: 'var(--ok)', padding: '5px 12px' }}
                onClick={() => api.openArtifact(lastResultPath)}
              >
                ▶ 立即打开查看
              </button>
              <button
                type="button"
                className="btn ghost sm"
                onClick={() => api.revealArtifact(lastResultPath)}
              >
                📂 浏览文件夹
              </button>
            </div>
          )}
        </div>
      )}

      {/* 异常报错提示 */}
      {directError && (
        <div className="card test-error-box" style={{ marginBottom: 20 }}>
          <strong>操作失败：</strong> {directError}
        </div>
      )}

      {/* 核心双列等宽工作台卡片容器 */}
      <div className="ppt-workbench">
        {/* ==================== 步骤一：生成 PPTX ==================== */}
        <div className="ppt-step-card">
          <div className="ppt-step-header">
            <h3 className="ppt-step-title">
              ✦ 步骤一：生成可编辑 PPTX
            </h3>
            <span className="badge done">原生 DrawingML 矢量</span>
          </div>

          <div className="row" style={{ gap: 8, marginBottom: 14 }}>
            <button
              type="button"
              className={`btn sm ${pptMode === 'text' ? '' : 'ghost'}`}
              onClick={() => setPptMode('text')}
            >
              直接粘贴 Markdown 文本
            </button>
            <button
              type="button"
              className={`btn sm ${pptMode === 'file' ? '' : 'ghost'}`}
              onClick={() => setPptMode('file')}
            >
              指定本地文档文件
            </button>
          </div>

          <form onSubmit={tab === 'direct' ? handleDirectPpt : handleAgentPpt} style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            {pptMode === 'text' ? (
              <div className="field" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <label>演示大纲与内容（Markdown）</label>
                <textarea
                  className="input mono"
                  rows={9}
                  style={{ minHeight: 220, resize: 'vertical', flex: 1 }}
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  placeholder="# 演示标题\n\n## 第一页\n- 要点1\n- 要点2"
                  required
                />
              </div>
            ) : (
              <div className="field" style={{ flex: 1 }}>
                <label>材料文档路径（支持 PDF / DOCX / Markdown / TXT）</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    className="input"
                    value={materialPath}
                    onChange={(e) => setMaterialPath(e.target.value)}
                    placeholder="请输入或点击右侧浏览选择本地文件，如 D:\docs\report.pdf"
                    style={{ flex: 1 }}
                    required
                  />
                  <input
                    ref={docFileInputRef}
                    type="file"
                    accept=".pdf,.docx,.doc,.md,.markdown,.txt"
                    style={{ display: 'none' }}
                    onChange={handleDocFileChange}
                  />
                  <button
                    type="button"
                    className="btn ghost"
                    style={{ flexShrink: 0, padding: '9px 14px', whiteSpace: 'nowrap' }}
                    onClick={() => docFileInputRef.current?.click()}
                  >
                    📁 浏览文件
                  </button>
                </div>
              </div>
            )}

            <div className="ppt-action-bar">
              <button className="btn" disabled={directLoading} style={{ width: '100%', justifyContent: 'center' }}>
                {tab === 'direct' ? '⚡ 一键直接生成 PPTX' : '🤖 创建 Agent 深度排版任务'}
              </button>
            </div>
          </form>
        </div>

        {/* ==================== 步骤二：PPT → 口播视频 ==================== */}
        <div className="ppt-step-card">
          <div className="ppt-step-header">
            <h3 className="ppt-step-title">
              🎬 步骤二：PPT → 口播视频
            </h3>
            <span className="badge pending">神经语音 + 4K 对齐</span>
          </div>

          <form onSubmit={tab === 'direct' ? handleDirectVideo : handleAgentVideo} style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            {/* PPT 路径选择（支持直接输入、浏览本地文件、快速点击已有产物） */}
            <div className="field">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label>PPTX 文件路径（本地磁盘或产物库）</label>
                {pptFiles.length > 0 && (
                  <span className="muted" style={{ fontSize: 12 }}>
                    产物库有 {pptFiles.length} 份 PPT
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input
                  className="input"
                  value={pptxInput}
                  onChange={(e) => setPptxInput(e.target.value)}
                  placeholder="可选择本地 PPTX 或输入相对路径，如 exports/presentation.pptx"
                  style={{ flex: 1 }}
                  required
                />
                <input
                  ref={pptxFileInputRef}
                  type="file"
                  accept=".pptx,.ppt"
                  style={{ display: 'none' }}
                  onChange={handlePptxFileChange}
                />
                <button
                  type="button"
                  className="btn ghost"
                  style={{ flexShrink: 0, padding: '9px 14px', whiteSpace: 'nowrap' }}
                  onClick={() => pptxFileInputRef.current?.click()}
                  title="从本地磁盘浏览并选择现有的 PPTX 文件"
                >
                  📁 浏览本地文件
                </button>
              </div>

              {/* 快速选用工作区已交付 PPT 胶囊列表 */}
              {pptFiles.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: 'var(--muted)', marginRight: 2 }}>快速选用：</span>
                  {pptFiles.slice(0, 4).map((f) => {
                    const active = pptxInput === f.path || pptxInput === f.name
                    return (
                      <button
                        key={f.path}
                        type="button"
                        className={`ppt-file-chip ${active ? 'active' : ''}`}
                        onClick={() => setPptxInput(f.path)}
                        title={`点击选用此 PPT：${f.name}`}
                      >
                        📑 {f.name}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* 宣讲音色选择 */}
            <div className="field">
              <label>宣讲口播音色（生动有感情的语言合成）</label>
              <select
                className="input"
                value={voice}
                style={{ width: '100%', boxSizing: 'border-box' }}
                onChange={(e) => {
                  setVoice(e.target.value)
                  if (e.target.value === 'piper') {
                    setTtsEngine('piper')
                  }
                }}
              >
                <option value="zh-CN-YunxiNeural">🎙️ 云希 · 激情宣讲 / 演说男声（推荐 · 抑扬顿挫富有感染力）</option>
                <option value="zh-CN-YunyangNeural">🎙️ 云扬 · 专业政务 / 新闻播音男声（沉稳大气、权威端庄）</option>
                <option value="zh-CN-XiaoxiaoNeural">🎙️ 晓晓 · 温暖亲切 / 知性讲解女声（温润自然、入情入理）</option>
                <option value="zh-CN-YunjianNeural">🎙️ 云健 · 磁性深沉 / 纪录片解说男声（高级质感、厚重有力）</option>
                <option value="zh-CN-XiaoyiNeural">🎙️ 晓伊 · 灵动欢快 / 叙事解说女声（节奏明快、生动活泼）</option>
                <option value="piper">💻 本地 Piper · 华研男声（完全纯离线 · 零网络依赖）</option>
              </select>
            </div>

            {/* 语速节奏与 TTS 引擎独立两列栅格，充足宽度，拒绝截断 */}
            <div className="ppt-select-grid">
              <div className="field" style={{ margin: 0 }}>
                <label>宣讲语速与节奏</label>
                <select
                  className="input"
                  value={speechRate}
                  onChange={(e) => setSpeechRate(e.target.value)}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                >
                  <option value="-4%">-4% · 从容稳健 (适合重要宣讲/大会汇报)</option>
                  <option value="+0%">0% · 黄金标准 (自然抑扬顿挫 · 推荐)</option>
                  <option value="+6%">+6% · 干练明快 (紧凑技术汇报)</option>
                </select>
              </div>

              <div className="field" style={{ margin: 0 }}>
                <label>TTS 引擎与容灾机制</label>
                <select
                  className="input"
                  value={ttsEngine}
                  onChange={(e) => setTtsEngine(e.target.value)}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                >
                  <option value="auto">智能双擎 (在线优先 + 离线Piper自动降级)</option>
                  <option value="edge">微软高品质 (Azure Neural 在线)</option>
                  <option value="piper">纯本地离线 (Piper 神经网络 · 零网络)</option>
                  <option value="cosyvoice">CosyVoice 本地大模型</option>
                </select>
              </div>
            </div>

            {/* 功能说明提示条 */}
            <div className="ppt-tip-box">
              ✦ 智能流水线将自动提取 PPT「演讲者备注 (Notes)」进行口语断句增强、标点韵律优化，通过高质量神经语音合成配音，并由内置 FFmpeg 完成音画精确对齐。无网络时全自动无缝降级到本地离线引擎，保障 100% 成功交付。
            </div>

            {/* 提交按钮 */}
            <div className="ppt-action-bar">
              <button
                className="btn"
                disabled={directLoading || !pptxInput.trim()}
                style={{ width: '100%', justifyContent: 'center' }}
              >
                {tab === 'direct' ? '🎬 启动本地视频渲染' : '🤖 创建 Agent 视频合成任务'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* 工作区已交付产物库 */}
      <div className="card" style={{ marginTop: 24, padding: '22px 24px' }}>
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>
            📦 工作区已交付产物库 ({workspaceFiles.length})
          </h3>
          <span className="muted" style={{ fontSize: 13 }}>
            PPT 演示文稿 ({pptFiles.length}) · 口播视频 ({videoFiles.length})
          </span>
        </div>

        {workspaceFiles.length === 0 ? (
          <div className="empty" style={{ padding: '32px', textAlign: 'center', color: 'var(--muted)' }}>
            暂无产物，生成后的 PPTX 与 MP4 将自动归档在这里，支持一键打开与查看。
          </div>
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
