interface ProgressBarProps {
  progress: number
  status?: string
  animated?: boolean
}

export default function ProgressBar({ progress, status, animated = true }: ProgressBarProps) {
  const isRunning = status === 'running' || status === 'planning'
  const isFailed = status === 'failed'
  const isDone = status === 'done' || progress >= 100

  let bgClass = 'var(--grad)'
  if (isFailed) bgClass = 'var(--err)'
  else if (isDone) bgClass = 'linear-gradient(135deg, #10b981 0%, #059669 100%)'

  return (
    <div className="progress-container">
      <div className="progress-header">
        <span className="progress-label">
          {isRunning ? '任务推进中…' : isDone ? '执行完成' : isFailed ? '执行终止' : '准备就绪'}
        </span>
        <span className="progress-value">{Math.min(100, Math.max(0, progress))}%</span>
      </div>
      <div className="progress-track">
        <div
          className={`progress-fill ${isRunning && animated ? 'progress-glow' : ''}`}
          style={{
            width: `${Math.min(100, Math.max(0, progress))}%`,
            background: bgClass,
          }}
        />
      </div>
    </div>
  )
}
