import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import ArtifactCard from '../components/ArtifactCard'

interface AvatarPreset {
  id: string
  name: string
  gender: string
  title: string
  avatar_badge: string
  default_voice: string
  description: string
  preview_color: string
  tags: string[]
}

const TEMPLATE_SCRIPTS = [
  {
    name: '金融与政务述职',
    avatar: 'boyang',
    voice: 'zh-CN-YunxiNeural',
    rate: '-2%',
    text: '尊敬的各位领导与同仁：大家好！现在向大家汇报本季度的重点业务进展与合规运行情况。本季度我们全面推行纯离线数字化架构，核心业务吞吐量稳步提升 35%，数据安全与私密性实现百分之百自闭环保障。'
  },
  {
    name: '前沿科技早报',
    avatar: 'wanqing',
    voice: 'zh-CN-XiaoxiaoNeural',
    rate: '+0%',
    text: '大家早上好，欢迎收听今日科技前沿早报。今天为您带来的是端侧离线 AI 技术的重大突破。全新一代轻量化端侧大模型已全面适配跨平台信创设备，在零网络连接的严苛环境下，依然可以实现精准高效的推理运算。'
  },
  {
    name: '在线课件培训',
    avatar: 'zhiming',
    voice: 'zh-CN-YunjianNeural',
    rate: '-4%',
    text: '同学们好！欢迎来到本期操作实战指南课程。今天我们将深入探讨系统核心模块的配置要点。请大家注意观察屏幕右下角的参数提示，严格遵循操作规范进行环境变量设置，确保每一个环节严谨可靠。'
  },
  {
    name: '文旅新潮推介',
    avatar: 'xinyue',
    voice: 'zh-CN-XiaoyiNeural',
    rate: '+3%',
    text: '哈喽小伙伴们！今天带大家沉浸式打卡充满历史记忆与科技魅力的兵工文旅小镇。这里不仅有壮观的工业遗址群，更有精彩绝伦的声光互动体验。快收拾好行囊，跟我一起开启这场奇妙的探索之旅吧！'
  }
]

export default function AvatarStudio() {
  const nav = useNavigate()
  const [presets, setPresets] = useState<AvatarPreset[]>([])
  const [selectedAvatarId, setSelectedAvatarId] = useState('boyang')
  const [mode, setMode] = useState<'standalone' | 'ppt_pip'>('standalone')

  // Avatar source: preset vs custom uploaded material
  const [avatarSourceMode, setAvatarSourceMode] = useState<'preset' | 'custom'>('preset')
  const [customAvatarPath, setCustomAvatarPath] = useState('')
  const [customAvatarName, setCustomAvatarName] = useState('')
  const [customAvatarType, setCustomAvatarType] = useState<'video' | 'image'>('video')
  const [customAvatarUrl, setCustomAvatarUrl] = useState('')
  const [customUploading, setCustomUploading] = useState(false)

  // Script text & editing mode
  const [scriptMode, setScriptMode] = useState<'write' | 'file' | 'llm'>('write')
  const [scriptText, setScriptText] = useState(
    '尊敬的各位嘉宾：大家好！欢迎体验纯离线数字人主播系统。本系统基于端到端神经网络声画对齐与动态唇形重构技术，保障 25 FPS 广播级画质与自然口播韵律。'
  )

  // LLM Script generation states
  const [coursewarePath, setCoursewarePath] = useState('')
  const [coursewareContent, setCoursewareContent] = useState('')
  const [llmStyle, setLlmStyle] = useState<'business' | 'academic' | 'teaching' | 'marketing'>('business')
  const [llmDuration, setLlmDuration] = useState<'1m' | '3m' | '5m'>('1m')
  const [llmGenerating, setLlmGenerating] = useState(false)
  const [llmSuccessMsg, setLlmSuccessMsg] = useState('')

  // Voice settings
  const [voice, setVoice] = useState('zh-CN-YunxiNeural')
  const [speechRate, setSpeechRate] = useState('+0%')
  const [ttsEngine, setTtsEngine] = useState('auto')

  // Background settings
  const [background, setBackground] = useState('studio_blue')
  const [customBgPath, setCustomBgPath] = useState('')
  const [chromaKey, setChromaKey] = useState(false)
  const [burnSubtitles, setBurnSubtitles] = useState(true)

  // PPT PiP settings
  const [pptxPath, setPptxPath] = useState('')
  const [pipPos, setPipPos] = useState<'bottom_right' | 'bottom_left' | 'top_right'>('bottom_right')
  const [pipStyle, setPipStyle] = useState<'circle' | 'rounded_rect' | 'rect'>('circle')
  const [pipScale, setPipScale] = useState(0.28)

  // File input refs
  const pptxFileInputRef = useRef<HTMLInputElement>(null)
  const bgFileInputRef = useRef<HTMLInputElement>(null)
  const customAvatarFileInputRef = useRef<HTMLInputElement>(null)
  const scriptFileInputRef = useRef<HTMLInputElement>(null)
  const coursewareFileInputRef = useRef<HTMLInputElement>(null)

  // Preview Workbench states
  const [previewTab, setPreviewTab] = useState<'video' | 'avatar' | 'subtitles'>('video')
  const [selectedPreviewVideoPath, setSelectedPreviewVideoPath] = useState('')
  const [selectedPreviewVideoUrl, setSelectedPreviewVideoUrl] = useState('')
  const videoPlayerRef = useRef<HTMLVideoElement>(null)

  // Progress & Execution states
  const [loading, setLoading] = useState(false)
  const [taskCreating, setTaskCreating] = useState(false)
  const [progressPercent, setProgressPercent] = useState(0)
  const [progressPhase, setProgressPhase] = useState(0) // 1 to 4
  const [currentPhaseText, setCurrentPhaseText] = useState('')
  const [statusMsg, setStatusMsg] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [lastResultPath, setLastResultPath] = useState('')
  const [createdTaskInfo, setCreatedTaskInfo] = useState<{ id: string; title: string } | null>(null)
  const progressTimerRef = useRef<any>(null)

  // Workspace files list
  const [workspaceFiles, setWorkspaceFiles] = useState<any[]>([])

  const loadPresets = useCallback(async () => {
    try {
      const res = await api.listAvatarPresets()
      if (res && res.presets) {
        setPresets(res.presets)
      }
    } catch {}
  }, [])

  const loadFiles = useCallback(async () => {
    try {
      const res = await api.listWorkspaceFiles()
      const files = res.files || []
      setWorkspaceFiles(files)

      // Auto-detect newest PPTX file if not yet specified
      const ppts = files.filter((f: any) => ['pptx', 'ppt'].includes(f.ext))
      if (ppts.length > 0 && !pptxPath) {
        setPptxPath(ppts[0].path)
      }

      // If no preview video selected, auto-select the latest MP4
      const vids = files.filter((f: any) => ['mp4', 'mov'].includes(f.ext))
      if (vids.length > 0 && !selectedPreviewVideoPath) {
        setSelectedPreviewVideoPath(vids[0].path)
        setSelectedPreviewVideoUrl(api.getArtifactUrl(vids[0].path))
      }
    } catch {}
  }, [pptxPath, selectedPreviewVideoPath])

  useEffect(() => {
    loadPresets()
    loadFiles()
    return () => {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
    }
  }, [loadPresets, loadFiles])

  // When anchor changes, update voice
  function handleSelectAvatar(preset: AvatarPreset) {
    setSelectedAvatarId(preset.id)
    setAvatarSourceMode('preset')
    if (preset.default_voice) {
      setVoice(preset.default_voice)
    }
  }

  // Apply script template
  function applyTemplate(tpl: typeof TEMPLATE_SCRIPTS[0]) {
    setScriptText(tpl.text)
    setSelectedAvatarId(tpl.avatar)
    setAvatarSourceMode('preset')
    setVoice(tpl.voice)
    setSpeechRate(tpl.rate)
  }

  // Handle custom avatar file selection (video or photo) with guaranteed workspace upload
  async function handleCustomAvatarFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const localPath = (file as any).path || ''
    const isVid = file.type.startsWith('video/') || /\.(mp4|mov|webm|mkv)$/i.test(file.name)
    setCustomAvatarName(file.name)
    setCustomAvatarType(isVid ? 'video' : 'image')

    const blobUrl = URL.createObjectURL(file)
    setCustomAvatarUrl(blobUrl)
    setAvatarSourceMode('custom')
    setSelectedAvatarId('custom')
    setPreviewTab('avatar')
    setErrorMsg('')

    if (localPath) {
      // 桌面客户端环境下，本地绝对路径可直接供后台 Python / FFmpeg 读取，无需额外 base64 上传
      setCustomAvatarPath(localPath)
      setCustomUploading(false)
      e.target.value = ''
      return
    }

    // Web 浏览器模式下：将素材传输至服务端工作区
    setCustomUploading(true)
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        try {
          const result = reader.result as string
          const base64 = result.includes(',') ? result.split(',')[1] : result
          const upRes = await api.uploadWorkspaceFile({
            filename: file.name,
            data_base64: base64
          })
          if (upRes && upRes.path) {
            setCustomAvatarPath(upRes.path)
          }
        } catch (err: any) {
          setErrorMsg(`素材保存失败：${err.message || '无法写入工作区'}`)
        } finally {
          setCustomUploading(false)
        }
      }
      reader.onerror = () => {
        setErrorMsg('素材读取失败，请检查文件权限')
        setCustomUploading(false)
      }
      reader.readAsDataURL(file)
    } catch (err: any) {
      setErrorMsg(`素材处理异常: ${err?.message || '未知错误'}`)
      setCustomUploading(false)
    }

    e.target.value = ''
  }

  // Handle narration script file import (.txt / .md / .docx / .pdf)
  function handleScriptFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result as string
      if (text) {
        setScriptText(text.trim())
        setScriptMode('write')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  // Handle courseware file selection for LLM script extraction
  function handleCoursewareFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const path = (file as any).path || file.name
    setCoursewarePath(path)
    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result as string
      if (text && typeof text === 'string') {
        setCoursewareContent(text.slice(0, 8000))
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  // Invoke LLM to generate professional narration script from courseware / notes
  async function handleGenerateScriptWithLLM() {
    const inputContent = coursewareContent.trim() || coursewarePath.trim()
    if (!inputContent) {
      setErrorMsg('请先输入课件或材料要点，或上传课件文件')
      return
    }

    setLlmGenerating(true)
    setErrorMsg('')
    setLlmSuccessMsg('')

    try {
      const res = await api.generateAvatarScript({
        content: inputContent,
        style: llmStyle,
        target_duration: llmDuration
      })

      if (res && res.script) {
        setScriptText(res.script)
        setLlmSuccessMsg(`✨ 大模型已成功提炼并生成 ${res.length} 字的专业口播脚本！`)
        setScriptMode('write')
      } else {
        throw new Error('未收到生成文案，请重试')
      }
    } catch (err: any) {
      setErrorMsg(err.message || '大模型生成文案失败，请检查输入或模型配置')
    } finally {
      setLlmGenerating(false)
    }
  }

  // Handle local background image/video selection
  function handleBgFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const path = (file as any).path || file.name
    setCustomBgPath(path)
    setBackground(path)
    e.target.value = ''
  }

  // Handle local PPTX file selection
  function handlePptxFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const path = (file as any).path || file.name
    setPptxPath(path)
    e.target.value = ''
  }

  // Build render payload with full validation
  function buildRenderPayload() {
    if (!scriptText.trim()) {
      throw new Error('请输入播报脚本与口播文案内容')
    }

    const payload: any = {
      mode,
      avatar_id: avatarSourceMode === 'custom' ? 'custom' : selectedAvatarId,
      text: scriptText.trim(),
      voice,
      rate: speechRate,
      tts_engine: ttsEngine,
      background: customBgPath || background,
      chroma_key: chromaKey,
      no_subtitles: !burnSubtitles,
    }

    if (avatarSourceMode === 'custom') {
      if (!customAvatarPath) {
        throw new Error('当前为自定义主播模式，请先点击「上传人物素材」选择视频或照片素材')
      }
      payload.custom_avatar_path = customAvatarPath
    }

    if (mode === 'ppt_pip') {
      if (!pptxPath.trim()) {
        throw new Error('PPT 画中画模式需要指定 PPTX 演示文稿路径')
      }
      payload.pptx_path = pptxPath.trim()
      payload.pip_pos = pipPos
      payload.pip_style = pipStyle
      payload.pip_scale = pipScale
    }

    return payload
  }

  // Start progress simulation milestones
  function startProgressSimulation() {
    setProgressPercent(12)
    setProgressPhase(1)
    setCurrentPhaseText('阶段 1/4：正在进行语义断句停顿优化与高质量语音母带合成...')

    let current = 12
    progressTimerRef.current = setInterval(() => {
      current += Math.floor(Math.random() * 5) + 3
      if (current >= 26 && current < 52) {
        setProgressPhase(2)
        setCurrentPhaseText('阶段 2/4：语音母带已生成，正在核验人脸底模与嘴周关键坐标...')
      } else if (current >= 52 && current < 76) {
        setProgressPhase(3)
        setCurrentPhaseText('阶段 3/4：正在推演神经网络 25FPS 逐帧声画动态唇形重构...')
      } else if (current >= 76 && current < 94) {
        setProgressPhase(4)
        setCurrentPhaseText('阶段 4/4：唇形重构就绪，正在进行音画封装与微黑底白字字幕烧录...')
      }
      if (current > 93) current = 93
      setProgressPercent(current)
    }, 1200)
  }

  function stopProgressSimulation(isSuccess: boolean) {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current)
      progressTimerRef.current = null
    }
    if (isSuccess) {
      setProgressPercent(100)
      setProgressPhase(4)
      setCurrentPhaseText('阶段 4/4：成片渲染全部完成，已成功交付归档！')
    }
  }

  // Action 1: Direct Local Synthesis (with real-time progress)
  async function handleDirectSynthesize(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setStatusMsg('')
    setErrorMsg('')
    setCreatedTaskInfo(null)

    try {
      const payload = buildRenderPayload()
      startProgressSimulation()

      const res = await api.renderAvatarVideo(payload)
      if (res.success || res.ok) {
        stopProgressSimulation(true)
        setStatusMsg(`✓ 数字人视频合成成功！产物已归档至：${res.output_path}`)
        setLastResultPath(res.output_path)
        setSelectedPreviewVideoPath(res.output_path)
        setSelectedPreviewVideoUrl(api.getArtifactUrl(res.output_path))
        setPreviewTab('video')
        await loadFiles()
      } else {
        throw new Error('合成未能完成，请检查输入或日志')
      }
    } catch (err: any) {
      stopProgressSimulation(false)
      setErrorMsg(err.message || '合成失败')
    } finally {
      setLoading(false)
    }
  }

  // Action 2: Multi-Task Dispatch (Adds task to /tasks for asynchronous concurrent processing)
  async function handleEnqueueTask() {
    setTaskCreating(true)
    setErrorMsg('')
    setStatusMsg('')
    try {
      const payload = buildRenderPayload()
      const res = await api.createAvatarTask(payload)
      if (res && res.task_id) {
        setCreatedTaskInfo({
          id: res.task_id,
          title: `数字人视频合成 (${payload.avatar_id} · ${payload.mode === 'ppt_pip' ? 'PPT画中画' : '独立全屏'})`
        })
        setStatusMsg(`✓ 已成功加入多任务队列！系统正在后台异步执行，可在「任务列表」中追踪多任务进度。`)
        await loadFiles()
      }
    } catch (err: any) {
      setErrorMsg(err.message || '加入任务列表失败')
    } finally {
      setTaskCreating(false)
    }
  }

  // Select a historical video to preview
  function handleSelectHistoricalVideo(file: any) {
    setSelectedPreviewVideoPath(file.path)
    setSelectedPreviewVideoUrl(api.getArtifactUrl(file.path))
    setPreviewTab('video')
  }

  const currentPreset = presets.find((p) => p.id === selectedAvatarId) || presets[0] || {
    id: 'boyang',
    name: '伯洋',
    title: '资深金融/政务男主播',
    avatar_badge: '权威沉稳',
    default_voice: 'zh-CN-YunxiNeural',
    description: '声音庄重清晰，适合政策解读与正式汇报。',
    preview_color: '#1e293b',
    tags: ['政务播报', '年终述职']
  }

  // Split script into clean subtitle preview sentences
  const subtitleSentences = scriptText
    .split(/([。！？!?\n]+)/)
    .filter(Boolean)
    .reduce((acc: string[], cur: string, idx: number, arr: string[]) => {
      if (idx % 2 === 0) {
        const punctuation = arr[idx + 1] || ''
        const full = (cur + punctuation).trim()
        if (full) acc.push(full)
      }
      return acc
    }, [])

  return (
    <div className="page" style={{ maxWidth: 1440, margin: '0 auto', paddingBottom: 60 }}>
      {/* 隐藏的本地文件拾取器 */}
      <input
        ref={customAvatarFileInputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/webm,image/png,image/jpeg,image/jpg"
        style={{ display: 'none' }}
        onChange={handleCustomAvatarFileSelected}
      />
      <input
        ref={scriptFileInputRef}
        type="file"
        accept=".txt,.md,.markdown,.docx,.doc,.pdf,.json"
        style={{ display: 'none' }}
        onChange={handleScriptFileSelected}
      />
      <input
        ref={coursewareFileInputRef}
        type="file"
        accept=".pptx,.ppt,.pdf,.docx,.doc,.md,.txt"
        style={{ display: 'none' }}
        onChange={handleCoursewareFileSelected}
      />
      <input
        ref={bgFileInputRef}
        type="file"
        accept="image/*,video/mp4,video/quicktime"
        style={{ display: 'none' }}
        onChange={handleBgFileSelected}
      />
      <input
        ref={pptxFileInputRef}
        type="file"
        accept=".pptx,.ppt"
        style={{ display: 'none' }}
        onChange={handlePptxFileSelected}
      />

      {/* Header Banner */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h2 style={{ margin: '0 0 6px', fontSize: 24, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 10 }}>
              <span>🧑‍💼</span> 离线数字人主播演播厅
              <span className="badge done" style={{ fontSize: 12, padding: '2px 8px' }}>
                纯离线 · 25 FPS 广播级
              </span>
              <span className="badge" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-2)', fontSize: 12, padding: '2px 8px' }}>
                多任务队列支持
              </span>
            </h2>
            <p className="muted" style={{ margin: 0, fontSize: 13.5 }}>
              结合端到端神经网络声画对齐、语义断句韵律增强、原材料上传与大模型智能提炼，支持实时进度追踪与多任务并发调度。
            </p>
          </div>
          <div>
            <button
              type="button"
              className="btn ghost sm"
              onClick={() => nav('/tasks')}
              title="前往系统多任务管理中心查看所有并发任务"
            >
              📋 打开多任务列表中心 →
            </button>
          </div>
        </div>
      </div>

      {/* Two-column workbench layout with minmax(0, 1fr) preventing component squeeze */}
      <div className="ppt-workbench" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.12fr) minmax(0, 0.88fr)', gap: 24 }}>
        {/* LEFT COLUMN: Configuration Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Section 1: Mode Selection */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontWeight: 600, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>🎬</span> 呈现模式
              </span>
              <span className="badge" style={{ fontSize: 11 }}>支持全屏独立演播及 PPT 伴读</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <button
                type="button"
                className={`btn ${mode === 'standalone' ? 'btn-primary' : 'ghost'}`}
                style={{
                  height: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  boxShadow: mode === 'standalone' ? undefined : 'none'
                }}
                onClick={() => setMode('standalone')}
              >
                <span>📺 全屏独立播报视频</span>
              </button>
              <button
                type="button"
                className={`btn ${mode === 'ppt_pip' ? 'btn-primary' : 'ghost'}`}
                style={{
                  height: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  boxShadow: mode === 'ppt_pip' ? undefined : 'none'
                }}
                onClick={() => setMode('ppt_pip')}
              >
                <span>🖼️ PPT 演示画中画陪讲</span>
              </button>
            </div>
          </div>

          {/* Section 2: Anchor Persona & Material Upload */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>🎭</span> 主播形象与人物原材料
              </span>
              <div style={{ display: 'inline-flex', background: 'var(--surface-2)', padding: 3, borderRadius: 8, border: '1px solid var(--border-2)' }}>
                <button
                  type="button"
                  style={{
                    border: 'none',
                    padding: '4px 12px',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                    fontWeight: 600,
                    background: avatarSourceMode === 'preset' ? 'var(--accent)' : 'transparent',
                    color: avatarSourceMode === 'preset' ? '#fff' : 'var(--text-2)'
                  }}
                  onClick={() => setAvatarSourceMode('preset')}
                >
                  🌟 精选预设主播
                </button>
                <button
                  type="button"
                  style={{
                    border: 'none',
                    padding: '4px 12px',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                    fontWeight: 600,
                    background: avatarSourceMode === 'custom' ? 'var(--accent)' : 'transparent',
                    color: avatarSourceMode === 'custom' ? '#fff' : 'var(--text-2)'
                  }}
                  onClick={() => {
                    setAvatarSourceMode('custom')
                    setSelectedAvatarId('custom')
                  }}
                >
                  👤 上传人物素材
                </button>
              </div>
            </div>

            {avatarSourceMode === 'preset' ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 12 }}>
                {(presets.length > 0 ? presets : [
                  { id: 'boyang', name: '伯洋', title: '资深金融/政务男主播', avatar_badge: '权威沉稳', default_voice: 'zh-CN-YunxiNeural', description: '声音庄重清晰，适合政策解读与正式汇报。', preview_color: '#1e293b', tags: ['政务播报', '年终述职'] },
                  { id: 'wanqing', name: '婉清', title: '优雅知性/新闻女主播', avatar_badge: '温和典雅', default_voice: 'zh-CN-XiaoxiaoNeural', description: '声线温润柔和，适合公司简介与科技早报。', preview_color: '#2d3748', tags: ['科技前沿', '品牌宣传'] },
                  { id: 'zhiming', name: '志明', title: '亲和商务/课件导师', avatar_badge: '亲和教学', default_voice: 'zh-CN-YunjianNeural', description: '表达生动亲切，适合微课与操作指南。', preview_color: '#1e3a5f', tags: ['培训课件', '操作指引'] },
                  { id: 'xinyue', name: '馨月', title: '青春活力/产品推介官', avatar_badge: '元气活力', default_voice: 'zh-CN-XiaoyiNeural', description: '声音灵动清脆，适合文旅宣传与新潮发布。', preview_color: '#3b1e3a', tags: ['文旅推广', '快闪发布'] },
                ]).map((p) => {
                  const isSelected = selectedAvatarId === p.id && avatarSourceMode === 'preset'
                  return (
                    <div
                      key={p.id}
                      onClick={() => handleSelectAvatar(p as any)}
                      style={{
                        padding: '14px',
                        borderRadius: 10,
                        border: isSelected ? '2px solid var(--accent)' : '1px solid var(--border-2)',
                        background: isSelected ? 'rgba(99, 102, 241, 0.06)' : 'var(--surface-2)',
                        cursor: 'pointer',
                        transition: 'all 0.18s ease',
                        position: 'relative'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div
                            style={{
                              width: 34,
                              height: 34,
                              borderRadius: '50%',
                              background: p.preview_color || '#333',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: '#fff',
                              fontWeight: 700,
                              fontSize: 14
                            }}
                          >
                            {p.name.slice(0, 1)}
                          </div>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: 14 }}>{p.name}</div>
                          </div>
                        </div>
                        <span
                          className="badge"
                          style={{
                            fontSize: 10.5,
                            background: isSelected ? 'var(--accent)' : 'rgba(0,0,0,0.06)',
                            color: isSelected ? '#fff' : 'inherit'
                          }}
                        >
                          {p.avatar_badge}
                        </span>
                      </div>
                      <div className="muted" style={{ fontSize: 11.5, marginBottom: 8, lineHeight: 1.4 }}>
                        {p.title}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {(p.tags || []).slice(0, 2).map((t, idx) => (
                          <span key={idx} style={{ fontSize: 10, padding: '2px 6px', background: 'rgba(0,0,0,0.04)', borderRadius: 4 }}>
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              /* Custom Avatar Material Upload Box */
              <div style={{ padding: '16px', background: 'var(--surface-2)', border: '1px dashed var(--border-2)', borderRadius: 10 }}>
                {customAvatarPath || customAvatarUrl ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      {customAvatarUrl ? (
                        customAvatarType === 'video' ? (
                          <video
                            src={customAvatarUrl}
                            style={{ width: 68, height: 68, borderRadius: 8, objectFit: 'cover', background: '#000' }}
                            muted
                            autoPlay
                            loop
                          />
                        ) : (
                          <img
                            src={customAvatarUrl}
                            alt="preview"
                            style={{ width: 68, height: 68, borderRadius: 8, objectFit: 'cover' }}
                          />
                        )
                      ) : (
                        <div style={{ width: 68, height: 68, borderRadius: 8, background: 'var(--accent-soft)', display: 'grid', placeItems: 'center', fontSize: 24 }}>
                          👤
                        </div>
                      )}
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text)' }}>{customAvatarName || '已选人物素材'}</div>
                        <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
                          {customAvatarType === 'video' ? '🎬 视频人物素材 (自动截帧循环)' : '🖼️ 高清肖像相片 (自动构建呼吸循环)'}
                        </div>
                        <div style={{ display: 'flex', gap: 6, marginTop: 4, alignItems: 'center' }}>
                          <span className="badge done" style={{ fontSize: 11 }}>
                            {customUploading ? '⏳ 正在写入工作区...' : '✅ 人物底模就绪'}
                          </span>
                          {customAvatarPath && (
                            <span className="muted mono" style={{ fontSize: 11 }}>已落盘</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        type="button"
                        className="btn ghost sm"
                        onClick={() => customAvatarFileInputRef.current?.click()}
                      >
                        重新上传素材
                      </button>
                      <button
                        type="button"
                        className="btn ghost sm"
                        style={{ color: 'var(--err)' }}
                        onClick={() => {
                          setCustomAvatarPath('')
                          setCustomAvatarUrl('')
                          setCustomAvatarName('')
                          setAvatarSourceMode('preset')
                          setSelectedAvatarId('boyang')
                        }}
                      >
                        清空
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    style={{ textAlign: 'center', padding: '24px 16px', cursor: 'pointer' }}
                    onClick={() => customAvatarFileInputRef.current?.click()}
                  >
                    <div style={{ fontSize: 32, marginBottom: 8 }}>📹 👤</div>
                    <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text)', marginBottom: 4 }}>
                      点击上传人物视频素材或高清正脸肖像照片
                    </div>
                    <p className="muted" style={{ fontSize: 12, margin: '0 0 12px' }}>
                      支持 MP4 / MOV 原生出镜视频（自动抽取底模循环）或 JPG / PNG 高清人像（自动构建生理微呼吸动作）
                    </p>
                    <button type="button" className="btn sm">
                      📁 浏览本地人物素材...
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Section 3: Script, File Import & LLM Generation */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>📝</span> 播报脚本与口播文案
              </span>
              <div style={{ display: 'inline-flex', background: 'var(--surface-2)', padding: 3, borderRadius: 8, border: '1px solid var(--border-2)' }}>
                <button
                  type="button"
                  style={{
                    border: 'none',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                    fontWeight: 600,
                    background: scriptMode === 'write' ? 'var(--accent)' : 'transparent',
                    color: scriptMode === 'write' ? '#fff' : 'var(--text-2)'
                  }}
                  onClick={() => setScriptMode('write')}
                >
                  ✍️ 手动编写
                </button>
                <button
                  type="button"
                  style={{
                    border: 'none',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                    fontWeight: 600,
                    background: scriptMode === 'file' ? 'var(--accent)' : 'transparent',
                    color: scriptMode === 'file' ? '#fff' : 'var(--text-2)'
                  }}
                  onClick={() => {
                    setScriptMode('file')
                    scriptFileInputRef.current?.click()
                  }}
                >
                  📄 导入脚本文件
                </button>
                <button
                  type="button"
                  style={{
                    border: 'none',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                    fontWeight: 600,
                    background: scriptMode === 'llm' ? 'var(--accent)' : 'transparent',
                    color: scriptMode === 'llm' ? '#fff' : 'var(--text-2)'
                  }}
                  onClick={() => setScriptMode('llm')}
                >
                  ✨ AI 提炼课件口播
                </button>
              </div>
            </div>

            {/* AI Courseware Script Extraction Drawer */}
            {scriptMode === 'llm' && (
              <div style={{ padding: '16px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.08) 100%)', border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: 10, marginBottom: 16 }}>
                <div style={{ fontWeight: 600, fontSize: 13.5, color: 'var(--accent)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>✨</span> 上传课件/材料，通过大模型一键提炼专业口播文案
                </div>
                <p className="muted" style={{ fontSize: 12, margin: '0 0 12px' }}>
                  支持上传 PPTX、PDF、Word 或 Markdown 文档，大模型将自动提炼核心论点，优化口播声律与自然过渡停顿。
                </p>

                {/* Upload courseware file row */}
                <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
                  <input
                    type="text"
                    className="input"
                    placeholder="可上传课件文件（PPTX / PDF / Word / TXT / Markdown）"
                    value={coursewarePath}
                    onChange={(e) => setCoursewarePath(e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <button
                    type="button"
                    className="btn ghost sm"
                    style={{ whiteSpace: 'nowrap', height: 42 }}
                    onClick={() => coursewareFileInputRef.current?.click()}
                  >
                    📁 上传课件文件
                  </button>
                </div>

                {/* Or paste content directly */}
                <textarea
                  className="input"
                  rows={3}
                  placeholder="或直接在此粘贴课件大纲、会议纪要、要点内容..."
                  value={coursewareContent}
                  onChange={(e) => setCoursewareContent(e.target.value)}
                  style={{ width: '100%', marginBottom: 12, fontSize: 12.5 }}
                />

                {/* Style and duration controls */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 14 }}>
                  <div>
                    <label className="muted" style={{ display: 'block', fontSize: 11.5, marginBottom: 4 }}>口播风格定位</label>
                    <select
                      className="input"
                      value={llmStyle}
                      onChange={(e) => setLlmStyle(e.target.value as any)}
                    >
                      <option value="business">💼 商务政务 (庄重大气)</option>
                      <option value="academic">🎓 学术微课 (严谨专业)</option>
                      <option value="teaching">🌟 通俗科普 (生动清晰)</option>
                      <option value="marketing">🚀 爆款推介 (节奏明快)</option>
                    </select>
                  </div>
                  <div>
                    <label className="muted" style={{ display: 'block', fontSize: 11.5, marginBottom: 4 }}>目标口播时长与篇幅</label>
                    <select
                      className="input"
                      value={llmDuration}
                      onChange={(e) => setLlmDuration(e.target.value as any)}
                    >
                      <option value="1m">⚡ 1 分钟精要速览 (~250字)</option>
                      <option value="3m">⏱️ 3 分钟标准宣讲 (~700字)</option>
                      <option value="5m">📖 5 分钟深度讲解 (~1200字)</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <button
                    type="button"
                    className="btn sm"
                    disabled={llmGenerating}
                    onClick={handleGenerateScriptWithLLM}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                  >
                    {llmGenerating ? (
                      <>
                        <span className="spinner" style={{ width: 14, height: 14, border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                        <span>大模型深度提炼中...</span>
                      </>
                    ) : (
                      <>
                        <span>✨ 启动大模型提炼口播文案</span>
                      </>
                    )}
                  </button>
                  {llmSuccessMsg && (
                    <span style={{ fontSize: 12, color: 'var(--ok)', fontWeight: 600 }}>{llmSuccessMsg}</span>
                  )}
                </div>
              </div>
            )}

            {/* Quick Templates Bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
              <span className="muted" style={{ fontSize: 12 }}>选用模板：</span>
              {TEMPLATE_SCRIPTS.map((tpl, i) => (
                <button
                  key={i}
                  type="button"
                  className="btn ghost sm"
                  style={{ padding: '3px 9px', fontSize: 11.5 }}
                  onClick={() => applyTemplate(tpl)}
                >
                  {tpl.name}
                </button>
              ))}
              <span className="muted" style={{ marginLeft: 'auto', fontSize: 12 }}>当前字数：{scriptText.length} 字</span>
            </div>

            <textarea
              className="input"
              rows={5}
              style={{ width: '100%', resize: 'vertical', lineHeight: 1.6, fontSize: 13.5, padding: '12px' }}
              value={scriptText}
              onChange={(e) => setScriptText(e.target.value)}
              placeholder="请输入数字人需要播报的文案内容，系统将自动进行语义呼吸切词与标点停顿注入..."
            />
          </div>

          {/* Section 4: Voice, Speed & Visual Options */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>🎙️</span> 声音表现与视觉合成配置
            </div>

            {/* Dropdown Grid: ample width, no font clipping, native chevron */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 16 }}>
              {/* Voice selector */}
              <div>
                <label className="muted" style={{ display: 'block', fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>
                  口播音色
                </label>
                <select
                  className="input"
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                >
                  <optgroup label="激情演讲 / 权威男声">
                    <option value="zh-CN-YunxiNeural">🎙️ 云希 · 激情演讲 (男声推荐)</option>
                    <option value="zh-CN-YunjianNeural">🎙️ 云健 · 沉稳专业 (影视旁白)</option>
                    <option value="zh-CN-YunyangNeural">🎙️ 云扬 · 新闻主持 (权威播报)</option>
                  </optgroup>
                  <optgroup label="优雅温和 / 知性女声">
                    <option value="zh-CN-XiaoxiaoNeural">🎙️ 晓晓 · 知性温和 (女声推荐)</option>
                    <option value="zh-CN-XiaoyiNeural">🎙️ 晓伊 · 青春活泼 (灵动女声)</option>
                  </optgroup>
                  <optgroup label="纯离线 Piper 独立音色">
                    <option value="zh_CN-huayan-medium">💻 华严 · 离线中性 (Piper内置)</option>
                  </optgroup>
                </select>
              </div>

              {/* Speech rate */}
              <div>
                <label className="muted" style={{ display: 'block', fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>
                  语速与口播节奏
                </label>
                <select
                  className="input"
                  value={speechRate}
                  onChange={(e) => setSpeechRate(e.target.value)}
                >
                  <option value="-8%">沉稳从容 (-8%)</option>
                  <option value="-4%">严谨汇报 (-4%)</option>
                  <option value="+0%">黄金标准 (0%)</option>
                  <option value="+4%">轻快活力 (+4%)</option>
                  <option value="+8%">快节奏解说 (+8%)</option>
                </select>
              </div>

              {/* TTS Strategy */}
              <div>
                <label className="muted" style={{ display: 'block', fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>
                  合成引擎策略
                </label>
                <select
                  className="input"
                  value={ttsEngine}
                  onChange={(e) => setTtsEngine(e.target.value)}
                >
                  <option value="auto">智能双擎 (优先在线 / 离线备选)</option>
                  <option value="piper">纯离线 Piper (零网络依赖)</option>
                </select>
              </div>

              {/* Background Preset (for standalone mode) */}
              {mode === 'standalone' && (
                <div>
                  <label className="muted" style={{ display: 'block', fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>
                    演播厅背景
                  </label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <select
                      className="input"
                      style={{ flex: 1 }}
                      value={background}
                      onChange={(e) => {
                        setBackground(e.target.value)
                        setCustomBgPath('')
                      }}
                    >
                      <option value="studio_blue">🏛️ 虚拟演播厅 (深蓝夜幕)</option>
                      <option value="tech_dark">🌃 极客科技 (深空暗灰)</option>
                      <option value="minimal_white">🏢 极简商务 (素雅纯白)</option>
                      <option value="none">👤 原生主播底模</option>
                      {customBgPath && <option value={customBgPath}>📁 自定义本地背景</option>}
                    </select>
                    <button
                      type="button"
                      className="btn ghost sm"
                      style={{ height: 42, padding: '0 12px', flexShrink: 0 }}
                      onClick={() => bgFileInputRef.current?.click()}
                      title="选择本地图片或视频作为背景"
                    >
                      浏览...
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* PPT PiP Settings (if mode === 'ppt_pip') */}
            {mode === 'ppt_pip' && (
              <div style={{ padding: '14px', background: 'var(--surface-2)', borderRadius: 8, marginBottom: 16 }}>
                <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>🖼️</span> 画中画叠加参数
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 10 }}>
                  <div>
                    <label className="muted" style={{ display: 'block', fontSize: 11.5, marginBottom: 4 }}>
                      PPT 文稿路径
                    </label>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <input
                        type="text"
                        className="input"
                        value={pptxPath}
                        onChange={(e) => setPptxPath(e.target.value)}
                        placeholder="exports/presentation.pptx"
                        style={{ flex: 1 }}
                      />
                      <button
                        type="button"
                        className="btn ghost sm"
                        style={{ height: 42, flexShrink: 0 }}
                        onClick={() => pptxFileInputRef.current?.click()}
                      >
                        选择...
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="muted" style={{ display: 'block', fontSize: 11.5, marginBottom: 4 }}>
                      画中画主播角位
                    </label>
                    <select
                      className="input"
                      value={pipPos}
                      onChange={(e) => setPipPos(e.target.value as any)}
                    >
                      <option value="bottom_right">右下角 (经典演讲位)</option>
                      <option value="bottom_left">左下角</option>
                      <option value="top_right">右上角</option>
                    </select>
                  </div>
                  <div>
                    <label className="muted" style={{ display: 'block', fontSize: 11.5, marginBottom: 4 }}>
                      窗口外观遮罩
                    </label>
                    <select
                      className="input"
                      value={pipStyle}
                      onChange={(e) => setPipStyle(e.target.value as any)}
                    >
                      <option value="circle">圆形徽章 (羽化抗锯齿)</option>
                      <option value="rounded_rect">圆角卡片 (白色细描边)</option>
                      <option value="rect">矩形窗口</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Checkbox Options */}
            <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={burnSubtitles}
                  onChange={(e) => setBurnSubtitles(e.target.checked)}
                />
                <span>烧录精准同步字幕（自动根据标点与呼吸节奏生成微黑底白字 SRT）</span>
              </label>

              {mode === 'standalone' && (
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={chromaKey}
                    onChange={(e) => setChromaKey(e.target.checked)}
                  />
                  <span>绿幕抠像合成（若主播底模为纯绿幕背景）</span>
                </label>
              )}
            </div>
          </div>

          {/* Action & Real-Time Progress Section */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontWeight: 600, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>🚀</span> 启动合成与多任务执行设计
              </span>
              <span className="muted" style={{ fontSize: 12 }}>支持即时渲染或加入多任务列表</span>
            </div>

            {/* Progress Stepper & Bar (Visible when loading or when progress > 0) */}
            {(loading || progressPercent > 0) && (
              <div style={{ marginBottom: 18, padding: '16px', background: 'var(--surface-2)', borderRadius: 10, border: '1px solid var(--border-2)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontWeight: 600, fontSize: 13.5, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    {loading && (
                      <span className="spinner" style={{ width: 14, height: 14, border: '2px solid var(--accent)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                    )}
                    <span>流水线阶段执行状态：{progressPercent}%</span>
                  </span>
                  <span className="badge done" style={{ fontSize: 11 }}>
                    {progressPhase === 1 && '第 1 阶段 · 语音母带'}
                    {progressPhase === 2 && '第 2 阶段 · 底模对齐'}
                    {progressPhase === 3 && '第 3 阶段 · 唇形重构'}
                    {progressPhase === 4 && (progressPercent === 100 ? '交付归档' : '第 4 阶段 · 音画封装')}
                  </span>
                </div>

                {/* Animated Progress Bar */}
                <div style={{ width: '100%', height: 8, background: 'rgba(0,0,0,0.08)', borderRadius: 4, overflow: 'hidden', marginBottom: 12 }}>
                  <div
                    style={{
                      width: `${progressPercent}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #6366f1 0%, #8b5cf6 50%, #10b981 100%)',
                      transition: 'width 0.4s ease',
                      borderRadius: 4
                    }}
                  />
                </div>

                {/* 4 Pipeline Stage Steppers */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, textAlign: 'center' }}>
                  <div style={{ padding: '6px 4px', borderRadius: 6, background: progressPhase >= 1 ? 'rgba(99, 102, 241, 0.1)' : 'rgba(0,0,0,0.03)', border: progressPhase === 1 ? '1px solid var(--accent)' : '1px solid transparent' }}>
                    <div style={{ fontSize: 11, fontWeight: progressPhase >= 1 ? 600 : 400, color: progressPhase >= 1 ? 'var(--accent)' : 'var(--muted)' }}>
                      1. 语音母带
                    </div>
                  </div>
                  <div style={{ padding: '6px 4px', borderRadius: 6, background: progressPhase >= 2 ? 'rgba(99, 102, 241, 0.1)' : 'rgba(0,0,0,0.03)', border: progressPhase === 2 ? '1px solid var(--accent)' : '1px solid transparent' }}>
                    <div style={{ fontSize: 11, fontWeight: progressPhase >= 2 ? 600 : 400, color: progressPhase >= 2 ? 'var(--accent)' : 'var(--muted)' }}>
                      2. 底模对齐
                    </div>
                  </div>
                  <div style={{ padding: '6px 4px', borderRadius: 6, background: progressPhase >= 3 ? 'rgba(99, 102, 241, 0.1)' : 'rgba(0,0,0,0.03)', border: progressPhase === 3 ? '1px solid var(--accent)' : '1px solid transparent' }}>
                    <div style={{ fontSize: 11, fontWeight: progressPhase >= 3 ? 600 : 400, color: progressPhase >= 3 ? 'var(--accent)' : 'var(--muted)' }}>
                      3. 唇形重构
                    </div>
                  </div>
                  <div style={{ padding: '6px 4px', borderRadius: 6, background: progressPhase >= 4 ? (progressPercent === 100 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(99, 102, 241, 0.1)') : 'rgba(0,0,0,0.03)', border: progressPhase === 4 ? '1px solid #10b981' : '1px solid transparent' }}>
                    <div style={{ fontSize: 11, fontWeight: progressPhase >= 4 ? 600 : 400, color: progressPhase >= 4 ? '#10b981' : 'var(--muted)' }}>
                      4. 音画交付
                    </div>
                  </div>
                </div>

                {currentPhaseText && (
                  <div className="muted" style={{ fontSize: 12, marginTop: 10, lineHeight: 1.4 }}>
                    {currentPhaseText}
                  </div>
                )}
              </div>
            )}

            {/* Dual Action Buttons: Direct vs Enqueue to Task List */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: 12 }}>
              <button
                type="button"
                className="btn btn-primary"
                style={{
                  height: 48,
                  fontSize: 15,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8
                }}
                disabled={loading || taskCreating || customUploading}
                onClick={handleDirectSynthesize}
              >
                {loading ? (
                  <>
                    <span className="spinner" style={{ width: 16, height: 16, border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                    <span>正在本地直接合成 ({progressPercent}%)...</span>
                  </>
                ) : (
                  <>
                    <span>✨ 本地极速直接合成</span>
                  </>
                )}
              </button>

              <button
                type="button"
                className="btn ghost"
                style={{
                  height: 48,
                  fontSize: 14,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8
                }}
                disabled={loading || taskCreating || customUploading}
                onClick={handleEnqueueTask}
                title="创建后台异步任务，加入多任务队列调度，支持多个视频排队或并发执行"
              >
                {taskCreating ? (
                  <>
                    <span className="spinner" style={{ width: 16, height: 16, border: '2px solid var(--accent)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                    <span>正在创建任务...</span>
                  </>
                ) : (
                  <>
                    <span>📋 加入多任务队列执行</span>
                  </>
                )}
              </button>
            </div>

            {/* Created Task Notification Banner */}
            {createdTaskInfo && (
              <div
                style={{
                  marginTop: 14,
                  padding: '12px 14px',
                  borderRadius: 8,
                  background: 'rgba(99, 102, 241, 0.08)',
                  border: '1px solid rgba(99, 102, 241, 0.25)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 10
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--accent)' }}>
                    ✓ 已将当前合成任务分发至多任务调度池
                  </div>
                  <div className="muted mono" style={{ fontSize: 11.5, marginTop: 2 }}>
                    任务ID: {createdTaskInfo.id} · {createdTaskInfo.title}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn sm"
                  onClick={() => nav(`/tasks/${createdTaskInfo.id}`)}
                >
                  查看任务详情 →
                </button>
              </div>
            )}

            {statusMsg && !createdTaskInfo && (
              <div
                style={{
                  marginTop: 12,
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                  color: '#065f46',
                  fontSize: 13
                }}
              >
                {statusMsg}
              </div>
            )}

            {errorMsg && (
              <div
                style={{
                  marginTop: 12,
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  color: '#991b1b',
                  fontSize: 13
                }}
              >
                ⚠️ {errorMsg}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Interactive Multi-Modal Audio-Visual Studio */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Main Interactive Studio Preview Card */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
              <div>
                <span style={{ fontWeight: 700, fontSize: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>📺</span> 数字人视听预览工作台
                </span>
                <span className="muted" style={{ fontSize: 12 }}>支持成片播放、素材底模审校与字幕对齐</span>
              </div>
              <div style={{ display: 'inline-flex', background: 'var(--surface-2)', padding: 3, borderRadius: 8, border: '1px solid var(--border-2)' }}>
                <button
                  type="button"
                  style={{
                    border: 'none',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                    fontWeight: 600,
                    background: previewTab === 'video' ? 'var(--accent)' : 'transparent',
                    color: previewTab === 'video' ? '#fff' : 'var(--text-2)'
                  }}
                  onClick={() => setPreviewTab('video')}
                >
                  🎬 成片播放
                </button>
                <button
                  type="button"
                  style={{
                    border: 'none',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                    fontWeight: 600,
                    background: previewTab === 'avatar' ? 'var(--accent)' : 'transparent',
                    color: previewTab === 'avatar' ? '#fff' : 'var(--text-2)'
                  }}
                  onClick={() => setPreviewTab('avatar')}
                >
                  👤 底模素材
                </button>
                <button
                  type="button"
                  style={{
                    border: 'none',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                    fontWeight: 600,
                    background: previewTab === 'subtitles' ? 'var(--accent)' : 'transparent',
                    color: previewTab === 'subtitles' ? '#fff' : 'var(--text-2)'
                  }}
                  onClick={() => setPreviewTab('subtitles')}
                >
                  📑 台词字幕
                </button>
              </div>
            </div>

            {/* TAB 1: Synthesized Video Player */}
            {previewTab === 'video' && (
              <div>
                {selectedPreviewVideoUrl || lastResultPath ? (
                  <div>
                    <div style={{ position: 'relative', width: '100%', borderRadius: 10, overflow: 'hidden', background: '#000', marginBottom: 12 }}>
                      <video
                        ref={videoPlayerRef}
                        src={selectedPreviewVideoUrl || api.getArtifactUrl(lastResultPath)}
                        controls
                        style={{ width: '100%', maxHeight: 340, display: 'block' }}
                      />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <span className="badge done" style={{ fontSize: 11 }}>25 FPS 广播级 1080P</span>
                        <span className="badge" style={{ fontSize: 11, background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent)' }}>
                          EBU R128 (-16 LUFS)
                        </span>
                        <span className="badge" style={{ fontSize: 11 }}>动态唇形对齐</span>
                      </div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {selectedPreviewVideoPath && (
                          <button
                            type="button"
                            className="btn ghost sm"
                            onClick={() => api.revealArtifact(selectedPreviewVideoPath)}
                            title="在系统资源管理器中定位文件"
                          >
                            📂 浏览文件
                          </button>
                        )}
                        {selectedPreviewVideoPath && (
                          <a
                            href={selectedPreviewVideoUrl || api.getArtifactUrl(selectedPreviewVideoPath)}
                            download
                            className="btn sm"
                            style={{ textDecoration: 'none' }}
                          >
                            ⬇️ 下载
                          </a>
                        )}
                      </div>
                    </div>
                    {selectedPreviewVideoPath && (
                      <div className="muted mono" style={{ fontSize: 11.5, background: 'var(--surface-2)', padding: '6px 10px', borderRadius: 6, wordBreak: 'break-all' }}>
                        {selectedPreviewVideoPath}
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '48px 20px', background: 'var(--surface-2)', borderRadius: 10, border: '1px dashed var(--border-2)' }}>
                    <div style={{ fontSize: 40, marginBottom: 10 }}>🎬 📺</div>
                    <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>暂无数字人成片可供播放</div>
                    <p className="muted" style={{ fontSize: 13, margin: '0 0 16px', maxWidth: 420, marginInline: 'auto' }}>
                      请在左侧设定主播、文案与音色后，点击「本地极速直接合成」；或者在下方交付产物库中点击已有视频直接调入播放。
                    </p>
                    <button
                      type="button"
                      className="btn sm"
                      onClick={handleDirectSynthesize}
                      disabled={loading}
                    >
                      ✨ 立即合成首支出镜成片
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: Anchor Raw Material Preview */}
            {previewTab === 'avatar' && (
              <div>
                {avatarSourceMode === 'custom' && customAvatarUrl ? (
                  <div>
                    <div style={{ position: 'relative', width: '100%', borderRadius: 10, overflow: 'hidden', background: '#0a0a0f', marginBottom: 12 }}>
                      {customAvatarType === 'video' ? (
                        <video
                          src={customAvatarUrl}
                          controls
                          autoPlay
                          loop
                          muted
                          style={{ width: '100%', maxHeight: 320, display: 'block', margin: '0 auto' }}
                        />
                      ) : (
                        <img
                          src={customAvatarUrl}
                          alt="custom anchor"
                          style={{ width: '100%', maxHeight: 320, objectFit: 'contain', display: 'block', margin: '0 auto' }}
                        />
                      )}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{customAvatarName}</div>
                        <div className="muted" style={{ fontSize: 12 }}>
                          {customAvatarType === 'video' ? '自采人物视频素材 · 往复平滑' : '自采单张人像素材 · 微动呼吸'}
                        </div>
                      </div>
                      <span className="badge done">底模就绪</span>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 14, padding: '12px 14px', background: 'var(--surface-2)', borderRadius: 10 }}>
                      <div
                        style={{
                          width: 54,
                          height: 54,
                          borderRadius: '50%',
                          background: currentPreset?.preview_color || '#333',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: '#fff',
                          fontWeight: 700,
                          fontSize: 22
                        }}
                      >
                        {currentPreset?.name?.slice(0, 1)}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 16 }}>{currentPreset?.name}</div>
                        <div className="muted" style={{ fontSize: 12 }}>{currentPreset?.title}</div>
                        <div style={{ fontSize: 11, color: 'var(--accent)', marginTop: 2 }}>{currentPreset?.avatar_badge}</div>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
                      <div style={{ padding: '10px 12px', background: 'var(--surface-2)', borderRadius: 8 }}>
                        <div className="muted" style={{ fontSize: 11 }}>采样频率</div>
                        <div style={{ fontWeight: 600, fontSize: 13, marginTop: 2 }}>25.0 FPS 广播级</div>
                      </div>
                      <div style={{ padding: '10px 12px', background: 'var(--surface-2)', borderRadius: 8 }}>
                        <div className="muted" style={{ fontSize: 11 }}>人脸唇形网格</div>
                        <div style={{ fontWeight: 600, fontSize: 13, marginTop: 2 }}>椭圆高斯羽化融合</div>
                      </div>
                      <div style={{ padding: '10px 12px', background: 'var(--surface-2)', borderRadius: 8 }}>
                        <div className="muted" style={{ fontSize: 11 }}>生理微动作</div>
                        <div style={{ fontWeight: 600, fontSize: 13, marginTop: 2 }}>自然呼吸 + 眨眼循环</div>
                      </div>
                      <div style={{ padding: '10px 12px', background: 'var(--surface-2)', borderRadius: 8 }}>
                        <div className="muted" style={{ fontSize: 11 }}>音频母带标准</div>
                        <div style={{ fontWeight: 600, fontSize: 13, marginTop: 2 }}>EBU R128 (-16 LUFS)</div>
                      </div>
                    </div>

                    <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.6, background: 'var(--surface-2)', padding: '12px', borderRadius: 8 }}>
                      {currentPreset?.description}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: Sentence-by-Sentence Subtitle & Timestamp Inspector */}
            {previewTab === 'subtitles' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <span className="muted" style={{ fontSize: 12 }}>字幕台词共 {subtitleSentences.length} 句（标点语义自动切分）</span>
                  <span className="badge done" style={{ fontSize: 11 }}>自动生成 SRT</span>
                </div>
                <div style={{ maxHeight: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {subtitleSentences.map((sentence, sIdx) => {
                    const estStartSec = sIdx * 3.2
                    const estEndSec = (sIdx + 1) * 3.2
                    const formatSec = (s: number) => {
                      const m = Math.floor(s / 60)
                      const sec = Math.floor(s % 60)
                      return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
                    }

                    return (
                      <div
                        key={sIdx}
                        onClick={() => {
                          if (videoPlayerRef.current) {
                            videoPlayerRef.current.currentTime = estStartSec
                            videoPlayerRef.current.play()
                          }
                          setPreviewTab('video')
                        }}
                        style={{
                          padding: '10px 12px',
                          borderRadius: 8,
                          background: 'var(--surface-2)',
                          border: '1px solid var(--border-2)',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        title="点击在播放器中跳转至该时间段"
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                          <span className="mono" style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600 }}>
                            [{formatSec(estStartSec)} - {formatSec(estEndSec)}]
                          </span>
                          <span className="muted" style={{ fontSize: 11 }}>#0{sIdx + 1}</span>
                        </div>
                        <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text)' }}>
                          {sentence}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Functional Architecture Assurance Box */}
          <div className="ppt-tip-box" style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.08) 100%)', border: '1px solid rgba(99, 102, 241, 0.2)', borderRadius: 12, padding: '18px 20px' }}>
            <div style={{ fontWeight: 700, fontSize: 14.5, marginBottom: 10, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>💡</span> 功能设计与核心技术保障说明
            </div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, lineHeight: 1.75, color: 'var(--text-2)' }}>
              <li>
                <strong>纯离线安全沙箱：</strong>自包含 Python 运行时与 ONNX Runtime 直接驱动本地算法，原材料、视频与文案绝不上云。
              </li>
              <li>
                <strong>多任务并发调度：</strong>支持点击「加入多任务队列执行」，系统自动创建任务记录并异步处理，可在任务列表统一管理。
              </li>
              <li>
                <strong>4阶段实时进度：</strong>实时展现「语音母带 → 底模对齐 → 唇形重构 → 音画封装」4 阶段进度条与毫秒级状态。
              </li>
              <li>
                <strong>25 FPS 画面流畅度：</strong>采用视频底模往复乒乓技术与高斯双向羽化融合，消除嘴周硬接缝与动作顿挫。
              </li>
            </ul>
          </div>

          {/* Deliverables Library (Videos & Documents) */}
          <div className="card" style={{ padding: '18px 20px', flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>📦</span> 交付产物库（点击可直接调入预览播放）
              </span>
              <button
                type="button"
                className="btn ghost sm"
                style={{ padding: '3px 8px', fontSize: 11.5 }}
                onClick={loadFiles}
              >
                刷新
              </button>
            </div>

            {workspaceFiles.length === 0 ? (
              <div className="muted" style={{ textAlign: 'center', padding: '30px 0', fontSize: 13 }}>
                暂无历史生成视频，点击左侧按钮立即生成第一支数字人视频
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 360, overflowY: 'auto' }}>
                {workspaceFiles
                  .filter((f) => ['mp4', 'mov', 'pptx'].includes(f.ext))
                  .slice(0, 10)
                  .map((f, idx) => {
                    const isPlaying = selectedPreviewVideoPath === f.path
                    return (
                      <div
                        key={idx}
                        onClick={() => ['mp4', 'mov'].includes(f.ext) && handleSelectHistoricalVideo(f)}
                        style={{
                          cursor: ['mp4', 'mov'].includes(f.ext) ? 'pointer' : 'default',
                          borderRadius: 8,
                          outline: isPlaying ? '2px solid var(--accent)' : 'none'
                        }}
                      >
                        <ArtifactCard path={f.path} name={f.name} size={f.size} compact />
                      </div>
                    )
                  })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
