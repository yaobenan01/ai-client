import { useCallback, useEffect, useRef, useState } from 'react'
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
  const [presets, setPresets] = useState<AvatarPreset[]>([])
  const [selectedAvatarId, setSelectedAvatarId] = useState('boyang')
  const [mode, setMode] = useState<'standalone' | 'ppt_pip'>('standalone')

  // Script text
  const [scriptText, setScriptText] = useState(
    '尊敬的各位嘉宾：大家好！欢迎体验纯离线数字人主播系统。本系统基于端到端神经网络声画对齐与动态唇形重构技术，保障 25 FPS 广播级画质与自然口播韵律。'
  )

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

  // Loading & statuses
  const [loading, setLoading] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [lastResultPath, setLastResultPath] = useState('')

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
      if (ppts.length > 0) {
        setPptxPath((prev) => (prev ? prev : ppts[0].path))
      }
    } catch {}
  }, [])

  useEffect(() => {
    loadPresets()
    loadFiles()
  }, [loadPresets, loadFiles])

  // When anchor changes, update voice
  function handleSelectAvatar(preset: AvatarPreset) {
    setSelectedAvatarId(preset.id)
    if (preset.default_voice) {
      setVoice(preset.default_voice)
    }
  }

  // Apply script template
  function applyTemplate(tpl: typeof TEMPLATE_SCRIPTS[0]) {
    setScriptText(tpl.text)
    setSelectedAvatarId(tpl.avatar)
    setVoice(tpl.voice)
    setSpeechRate(tpl.rate)
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

  // Handle digital human synthesis
  async function handleSynthesize(e: React.FormEvent) {
    e.preventDefault()
    if (!scriptText.trim()) return

    setLoading(true)
    setStatusMsg('')
    setErrorMsg('')
    setLastResultPath('')

    try {
      const payload: any = {
        mode,
        avatar_id: selectedAvatarId,
        text: scriptText.trim(),
        voice,
        rate: speechRate,
        tts_engine: ttsEngine,
        background: customBgPath || background,
        chroma_key: chromaKey,
        no_subtitles: !burnSubtitles,
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

      setStatusMsg('🚀 正在启动纯离线数字人渲染管线（语音母带生成 -> 25FPS 唇形重构 -> 画面合成）...')
      const res = await api.renderAvatarVideo(payload)

      if (res.success || res.ok) {
        setStatusMsg(`✓ 数字人视频合成成功！产物已归档至：${res.output_path}`)
        setLastResultPath(res.output_path)
        await loadFiles()
      } else {
        throw new Error('合成未能完成，请检查输入或日志')
      }
    } catch (err: any) {
      setErrorMsg(err.message || '合成失败')
    } finally {
      setLoading(false)
    }
  }

  const currentPreset = presets.find((p) => p.id === selectedAvatarId) || presets[0]

  return (
    <div className="page" style={{ maxWidth: 1440, margin: '0 auto', paddingBottom: 60 }}>
      {/* 隐藏的本地文件拾取器 */}
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
              <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.25)', fontSize: 12, padding: '2px 8px' }}>
                纯离线 · 25 FPS
              </span>
            </h2>
            <p className="muted" style={{ margin: 0, fontSize: 13.5 }}>
              结合端到端神经网络声画对齐、语义断句韵律增强与 EBU R128 广播级母带，全流程无需联网，百分之百保障企业资产私密安全。
            </p>
          </div>
        </div>
      </div>

      {/* Two-column workbench layout with minmax(0, 1fr) preventing component squeeze */}
      <div className="ppt-workbench" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.15fr) minmax(0, 0.85fr)', gap: 24 }}>
        {/* LEFT COLUMN: Configuration Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Section 1: Mode Selection */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontWeight: 600, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>🎬</span> 呈现模式
              </span>
              <span className="badge" style={{ fontSize: 11 }}>支持全屏及 PPT 演说</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <button
                type="button"
                className={`btn ${mode === 'standalone' ? 'btn-primary' : ''}`}
                style={{
                  height: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  border: mode === 'standalone' ? 'none' : '1px solid var(--border)'
                }}
                onClick={() => setMode('standalone')}
              >
                <span>📺 全屏独立播报视频</span>
              </button>
              <button
                type="button"
                className={`btn ${mode === 'ppt_pip' ? 'btn-primary' : ''}`}
                style={{
                  height: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  border: mode === 'ppt_pip' ? 'none' : '1px solid var(--border)'
                }}
                onClick={() => setMode('ppt_pip')}
              >
                <span>🖼️ PPT 演示画中画陪讲</span>
              </button>
            </div>
          </div>

          {/* Section 2: Anchor Persona Cards */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontWeight: 600, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>🎭</span> 预设精品数字人主播
              </span>
              <span className="muted" style={{ fontSize: 12 }}>点击卡片即可直接切换</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 12 }}>
              {(presets.length > 0 ? presets : [
                { id: 'boyang', name: '伯洋', title: '资深金融/政务男主播', avatar_badge: '权威沉稳', default_voice: 'zh-CN-YunxiNeural', description: '声音庄重清晰，适合政策解读与正式汇报。', preview_color: '#1e293b', tags: ['政务播报', '年终述职'] },
                { id: 'wanqing', name: '婉清', title: '优雅知性/新闻女主播', avatar_badge: '温和典雅', default_voice: 'zh-CN-XiaoxiaoNeural', description: '声线温润柔和，适合公司简介与科技早报。', preview_color: '#2d3748', tags: ['科技前沿', '品牌宣传'] },
                { id: 'zhiming', name: '志明', title: '亲和商务/课件导师', avatar_badge: '亲和教学', default_voice: 'zh-CN-YunjianNeural', description: '表达生动亲切，适合微课与操作指南。', preview_color: '#1e3a5f', tags: ['培训课件', '操作指引'] },
                { id: 'xinyue', name: '馨月', title: '青春活力/产品推介官', avatar_badge: '元气活力', default_voice: 'zh-CN-XiaoyiNeural', description: '声音灵动清脆，适合文旅宣传与新潮发布。', preview_color: '#3b1e3a', tags: ['文旅推广', '快闪发布'] },
              ]).map((p) => {
                const isSelected = selectedAvatarId === p.id
                return (
                  <div
                    key={p.id}
                    onClick={() => handleSelectAvatar(p as any)}
                    style={{
                      padding: '14px',
                      borderRadius: 10,
                      border: isSelected ? '2px solid var(--accent)' : '1px solid var(--border)',
                      background: isSelected ? 'rgba(99, 102, 241, 0.06)' : 'var(--card-bg, #fff)',
                      cursor: 'pointer',
                      transition: 'all 0.18s ease',
                      position: 'relative'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            background: p.preview_color || '#333',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#fff',
                            fontWeight: 700,
                            fontSize: 13
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
          </div>

          {/* Section 3: Script & Narration Content */}
          <div className="card" style={{ padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <span style={{ fontWeight: 600, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>📝</span> 播报脚本与口播文案
              </span>
              <span className="muted" style={{ fontSize: 12 }}>已输入 {scriptText.length} 字</span>
            </div>

            {/* Quick Templates */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
              <span className="muted" style={{ fontSize: 12 }}>常用模板：</span>
              {TEMPLATE_SCRIPTS.map((tpl, i) => (
                <button
                  key={i}
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: '4px 10px', fontSize: 11.5, height: 'auto' }}
                  onClick={() => applyTemplate(tpl)}
                >
                  {tpl.name}
                </button>
              ))}
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

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 16 }}>
              {/* Voice selector */}
              <div>
                <label className="muted" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>
                  口播音色
                </label>
                <select
                  className="input"
                  style={{ width: '100%', height: 38 }}
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                >
                  <optgroup label="激情演讲 / 权威男声">
                    <option value="zh-CN-YunxiNeural">云希 · 激情宣讲 / 演说男声 (推荐)</option>
                    <option value="zh-CN-YunjianNeural">云健 · 沉稳专业 / 影视旁白</option>
                    <option value="zh-CN-YunyangNeural">云扬 · 专业新闻播音主持</option>
                  </optgroup>
                  <optgroup label="优雅温和 / 知性女声">
                    <option value="zh-CN-XiaoxiaoNeural">晓晓 · 知性温和 / 优雅女声</option>
                    <option value="zh-CN-XiaoyiNeural">晓伊 · 青春活泼 / 灵动女声</option>
                  </optgroup>
                  <optgroup label="纯离线 Piper 独立音色">
                    <option value="zh_CN-huayan-medium">华严 · 离线中性教学音色</option>
                  </optgroup>
                </select>
              </div>

              {/* Speech rate */}
              <div>
                <label className="muted" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>
                  语速与口播节奏
                </label>
                <select
                  className="input"
                  style={{ width: '100%', height: 38 }}
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
                <label className="muted" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>
                  合成引擎策略
                </label>
                <select
                  className="input"
                  style={{ width: '100%', height: 38 }}
                  value={ttsEngine}
                  onChange={(e) => setTtsEngine(e.target.value)}
                >
                  <option value="auto">智能双擎 (在线神经音色，离线无缝降级)</option>
                  <option value="piper">纯离线 Piper (零联网强制依赖)</option>
                </select>
              </div>

              {/* Background Preset (for standalone mode) */}
              {mode === 'standalone' && (
                <div>
                  <label className="muted" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>
                    演播厅背景
                  </label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <select
                      className="input"
                      style={{ flex: 1, height: 38 }}
                      value={background}
                      onChange={(e) => {
                        setBackground(e.target.value)
                        setCustomBgPath('')
                      }}
                    >
                      <option value="studio_blue">🏛️ 虚拟演播厅 (深蓝夜幕)</option>
                      <option value="tech_dark">🌃 极客科技 (深空暗灰)</option>
                      <option value="minimal_white">🏢 极简商务 (素雅纯白)</option>
                      <option value="none">👤 原生主播底镜</option>
                      {customBgPath && <option value={customBgPath}>📁 自定义本地背景</option>}
                    </select>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ height: 38, padding: '0 10px', fontSize: 12, whiteSpace: 'nowrap' }}
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
              <div style={{ padding: '14px', background: 'rgba(0,0,0,0.03)', borderRadius: 8, marginBottom: 16 }}>
                <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>🖼️</span> 画中画叠加参数
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 10 }}>
                  <div>
                    <label className="muted" style={{ display: 'block', fontSize: 11.5, marginBottom: 4 }}>
                      PPT 文稿路径
                    </label>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <input
                        type="text"
                        className="input"
                        style={{ flex: 1, height: 34, fontSize: 12 }}
                        value={pptxPath}
                        onChange={(e) => setPptxPath(e.target.value)}
                        placeholder="exports/presentation.pptx"
                      />
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ height: 34, padding: '0 8px', fontSize: 11.5 }}
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
                      style={{ width: '100%', height: 34, fontSize: 12 }}
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
                      style={{ width: '100%', height: 34, fontSize: 12 }}
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
                <span>烧录精准同步字幕（自动根据停顿生成微黑底白字 SRT）</span>
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

          {/* Action Button */}
          <div>
            <button
              type="button"
              className="btn btn-primary"
              style={{
                width: '100%',
                height: 48,
                fontSize: 16,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 10
              }}
              disabled={loading}
              onClick={handleSynthesize}
            >
              {loading ? (
                <>
                  <span className="spinner" style={{ width: 18, height: 18, border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                  <span>正在全力离线合成中，请稍候...</span>
                </>
              ) : (
                <>
                  <span>✨ 启动离线数字人视频合成</span>
                </>
              )}
            </button>

            {statusMsg && (
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

        {/* RIGHT COLUMN: Functional Guide & Artifacts Preview */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Functional Instructions Box */}
          <div className="ppt-tip-box" style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.08) 100%)', border: '1px solid rgba(99, 102, 241, 0.2)', borderRadius: 12, padding: '20px' }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 12, color: 'var(--accent, #6366f1)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>💡</span> 功能设计与核心技术保障说明
            </div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.8, color: 'var(--text-secondary, #475569)' }}>
              <li>
                <strong>纯离线安全沙箱：</strong>通过自包含 Python 运行时与 ONNX Runtime 直接驱动本地算法模型，文案与声画绝不上传云端，完全满足金融与政务内网安全保密需求。
              </li>
              <li>
                <strong>25 FPS 画面流畅度：</strong>采用视频底模往复乒乓循环技术，配合椭圆高斯羽化融合遮罩与 EMA 时域平滑滤波，消除嘴周方形硬接缝与动作顿挫。
              </li>
              <li>
                <strong>动态呼吸与广播级人声：</strong>根据标点符号自动计算生理呼吸停顿，并施加 75Hz 高通滤波、共鸣均衡、动态压限以及 EBU R128 (-16 LUFS) 响度标准化。
              </li>
              <li>
                <strong>开箱即用与容灾降级：</strong>模型缺失时自动启动高保真声学几何唇形引擎，保障生产流水线永不中断崩溃。
              </li>
            </ul>
          </div>

          {/* Current Selection Status Summary */}
          <div className="card" style={{ padding: '18px 20px' }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>
              <span>📌</span> 当前选定主播信息
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }}>
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: '50%',
                  background: currentPreset?.preview_color || '#333',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: 20
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
            <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.5, background: 'rgba(0,0,0,0.02)', padding: '10px 12px', borderRadius: 6 }}>
              {currentPreset?.description}
            </div>
          </div>

          {/* Recent Video Deliverables */}
          <div className="card" style={{ padding: '18px 20px', flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>
                <span>📦</span> 交付产物库（视频 & 文档）
              </span>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '3px 8px', fontSize: 11.5, height: 'auto' }}
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
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 420, overflowY: 'auto' }}>
                {workspaceFiles
                  .filter((f) => ['mp4', 'mov', 'pptx'].includes(f.ext))
                  .slice(0, 8)
                  .map((f, idx) => (
                    <ArtifactCard key={idx} path={f.path} name={f.name} size={f.size} compact />
                  ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
