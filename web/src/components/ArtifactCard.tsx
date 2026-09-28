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

export default function ArtifactCard({ path, name, size, compact = false }: ArtifactCardProps) {
  const [copied, setCopied] = useState(false)
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

  if (compact) {
    return (
      <div className="artifact-pill">
        <span className="artifact-icon">{icon}</span>
        <span className="artifact-name mono">{filename}</span>
        <a href={downloadUrl} target="_blank" rel="noreferrer" className="artifact-action" download={filename}>
          下载
        </a>
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
        <a href={downloadUrl} target="_blank" rel="noreferrer" className="btn sm" download={filename}>
          📥 下载产物
        </a>
        <button className="btn ghost sm" onClick={copyPath}>
          {copied ? '✓ 已复制路径' : '复制文件路径'}
        </button>
      </div>
    </div>
  )
}
