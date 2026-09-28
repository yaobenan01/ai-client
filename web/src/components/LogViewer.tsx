import { useState } from 'react'

export interface TaskStep {
  step: number
  action: string
  tool_name?: string
  input?: string
  output?: string
  timestamp: number
}

interface LogViewerProps {
  logsJson?: string | null
}

const ACTION_MAP: Record<string, { label: string; icon: string; badgeClass: string }> = {
  thought: { label: '思维分析', icon: '🧠', badgeClass: 'step-badge-thought' },
  tool_call: { label: '调用工具', icon: '⚡', badgeClass: 'step-badge-call' },
  tool_result: { label: '工具返回', icon: '📦', badgeClass: 'step-badge-result' },
  finish: { label: '交付结论', icon: '✦', badgeClass: 'step-badge-finish' },
  error: { label: '执行异常', icon: '⚠️', badgeClass: 'step-badge-error' },
}

export default function LogViewer({ logsJson }: LogViewerProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  let steps: TaskStep[] = []
  try {
    if (logsJson) {
      steps = typeof logsJson === 'string' ? JSON.parse(logsJson) : logsJson
    }
  } catch {
    steps = []
  }

  function toggle(idx: number) {
    setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  if (!steps || steps.length === 0) {
    return (
      <div className="log-empty">
        <span className="muted">暂无分步日志，任务执行时将实时流式记录思考与工具调用轨迹。</span>
      </div>
    )
  }

  return (
    <div className="timeline-wrap">
      <div className="timeline-head">
        <span className="timeline-title">Agent 规划与工具执行轨迹（共 {steps.length} 个节点）</span>
        <button
          className="btn ghost sm"
          onClick={() => {
            const allExpanded = Object.keys(expanded).length === steps.length
            if (allExpanded) setExpanded({})
            else {
              const full: Record<number, boolean> = {}
              steps.forEach((_, i) => (full[i] = true))
              setExpanded(full)
            }
          }}
        >
          {Object.keys(expanded).length === steps.length ? '折叠全部' : '展开全部'}
        </button>
      </div>

      <div className="timeline">
        {steps.map((st, idx) => {
          const meta = ACTION_MAP[st.action] || { label: st.action, icon: '•', badgeClass: 'step-badge-thought' }
          const isExp = expanded[idx] ?? (st.action === 'finish' || st.action === 'error' || idx === steps.length - 1)
          const timeStr = st.timestamp ? new Date(st.timestamp * 1000).toLocaleTimeString() : ''

          return (
            <div className={`timeline-item ${st.action}`} key={idx}>
              <div className="timeline-marker">
                <span>{meta.icon}</span>
              </div>
              <div className="timeline-card">
                <div className="timeline-header" onClick={() => toggle(idx)}>
                  <div className="timeline-header-left">
                    <span className={`step-badge ${meta.badgeClass}`}>{meta.label}</span>
                    {st.tool_name && <span className="mono tool-pill">{st.tool_name}</span>}
                    <span className="step-num">Step {st.step}</span>
                  </div>
                  <div className="timeline-header-right">
                    <span className="muted time-label">{timeStr}</span>
                    <span className="arrow-toggle">{isExp ? '▲' : '▼'}</span>
                  </div>
                </div>

                {isExp && (
                  <div className="timeline-content">
                    {st.input && (
                      <div className="code-block-wrap">
                        <div className="code-label">输入参数</div>
                        <pre className="code-block mono">{st.input}</pre>
                      </div>
                    )}
                    {st.output && (
                      <div className="code-block-wrap">
                        <div className="code-label">输出结果 / 内容</div>
                        <pre className="code-block mono">{st.output}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
