import { useState } from 'react'
import { api } from '../lib/api'

interface ArtifactCardProps {
  path: string
  name?: string
  size?: number
  compact?: boolean
}

function formatSize(bytes?: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/// 桌面端（Tauri）里文件就在本机，直接打开比“下载”更合理。
const isDesktop =
  typeof window !== 'undefined' &&
  ('__TAURI_INTERNALS__' in window ||
    '__TAURI__' in window ||
    window.location.hostname === 'tauri.localhost' ||
    window.location.protocol === 'tauri:')

export default function ArtifactCard({ path, name, size, compact = false }: ArtifactCardProps) {
  const [copied, setCopied] = useState(false)
  const [busy, setBusy] = useState<'' | 'open' | 'reveal' | 'download'>('')
  const [err, setErr] = useState('')

  const filename = name || path.split(/[/\\]/).pop() || path
  const ext = filename.split('.').pop()?.toLowerCase() || ''

  const isPpt = ext === 'pptx' || ext === 'ppt'
  const isVideo = ext === 'mp4' || ext === 'webm' || ext === 'mkv'
  const isPdf = ext === 'pdf'

  const icon = isPpt ? '📊' : isVideo ? '🎬' : isPdf ? '📑' : '📄'
  const tagColor = isPpt ? 'artifact-tag-ppt' : isVideo ? 'artifact-tag-video' : 'artifact-tag-other'
  const tagText = isPpt ? '可编辑 PPTX' : isVideo ? '口播 MP4' : isPdf ? 'PDF 文档' : ext.toUpperCase()

  const downloadUrl = api.getArtifactUrl(path)

  async function copyPath() {
    try {
      await navigator.clipboard.writeText(path)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  async function openFile() {
    setErr('')
    setBusy('open')
    try {
      await api.openArtifact(path)
    } catch (e: any) {
      setErr(`打开失败：${e?.message || e}`)
    } finally {
      setBusy('')
    }
  }

  async function revealFolder() {
    setErr('')
    setBusy('reveal')
    try {
      await api.revealArtifact(path)
    } catch (e: any) {
      setErr(`打开文件夹失败：${e?.message || e}`)
    } finally {
      setBusy('')
    }
  }

  async function download() {
    setErr('')
    setBusy('download')
    try {
      // 用 fetch + blob 触发保存：跨源 <a download> 在桌面 WebView 里会被忽略
      const res = await fetch(downloadUrl, { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 5000)
    } catch (e: any) {
      setErr(
        isDesktop
          ? `下载失败：${e?.message || e}（桌面端建议用「打开文件」或「打开文件夹」）`
          : `下载失败：${e?.message || e}`,
      )
    } finally {
      setBusy('')
    }
  }

  if (compact) {
    return (
      <div className="artifact-pill">
        <span className="artifact-icon">{icon}</span>
        <span className="artifact-name mono">{filename}</span>
        <button className="artifact-action" onClick={openFile} disabled={busy !== ''}>
          打开
        </button>
      </div>
    )
  }

  return (
    <div className="artifact-card">
      <div className="artifact-header">
        <span className="artifact-icon-lg">{icon}</span>
        <div className="artifact-info">
          <div className="artifact-title mono" title={filename}>
            {filename}
          </div>
          <div className="artifact-sub">
            <span className={`artifact-tag ${tagColor}`}>{tagText}</span>
            {size ? <span className="muted">{formatSize(size)}</span> : null}
            <span className="muted mono" style={{ fontSize: 11 }}>
              {path}
            </span>
          </div>
        </div>
      </div>

      <div className="artifact-actions">
        <button className="btn sm" onClick={openFile} disabled={busy !== ''}>
          {busy === 'open' ? '打开中…' : '📂 打开文件'}
        </button>
        <button className="btn ghost sm" onClick={revealFolder} disabled={busy !== ''}>
          {busy === 'reveal' ? '定位中…' : '🗂 打开文件夹'}
        </button>
        <button className="btn ghost sm" onClick={download} disabled={busy !== ''}>
          {busy === 'download' ? '下载中…' : '📥 下载产物'}
        </button>
        <button className="btn ghost sm" onClick={copyPath}>
          {copied ? '✓ 已复制路径' : '复制文件路径'}
        </button>
      </div>

      {err && (
        <div className="artifact-error" style={{ color: 'var(--err)', fontSize: 12, marginTop: 8 }}>
          {err}
        </div>
      )}
    </div>
  )
}
