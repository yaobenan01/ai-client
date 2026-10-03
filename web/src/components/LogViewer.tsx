import { useState, useMemo } from 'react'

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

interface ToolOperation {
  input?: string
  output?: string
  isError?: boolean
  timestamp: number
}

interface UnifiedStep {
  id: string
  step: number
  action: 'thought' | 'tool' | 'finish' | 'error'
  tool_name?: string
  label: string
  icon: string
  badgeClass: string
  timestamp: number
  thoughtContent?: string
  operations: ToolOperation[]
}

const ACTION_MAP: Record<string, { label: string; icon: string; badgeClass: string }> = {
  thought: { label: '思维分析', icon: '🧠', badgeClass: 'step-badge-thought' },
  tool: { label: '调用工具', icon: '⚡', badgeClass: 'step-badge-call' },
  finish: { label: '交付结论', icon: '✦', badgeClass: 'step-badge-finish' },
  error: { label: '执行异常', icon: '⚠️', badgeClass: 'step-badge-error' },
}

/** 提炼工具参数或结果的极简摘要标签（如文件名、路径） */
function extractSummary(tool_name: string | undefined, inputStr: string | undefined): string {
  if (!inputStr) return ''
  try {
    const parsed = JSON.parse(inputStr)
    if (parsed.path) return String(parsed.path)
    if (parsed.file_path) return String(parsed.file_path)
    if (parsed.input_path) return String(parsed.input_path)
    if (parsed.pptx_path) return String(parsed.pptx_path)
    if (parsed.cmd) return String(parsed.cmd)
    if (parsed.content) return String(parsed.content).slice(0, 30) + '...'
  } catch {
    // 非 JSON 文本
  }
  return inputStr.length > 40 ? inputStr.slice(0, 40) + '...' : inputStr
}

export default function LogViewer({ logsJson }: LogViewerProps) {
  const [mergeSteps, setMergeSteps] = useState(true)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const rawSteps: TaskStep[] = useMemo(() => {
    if (!logsJson) return []
    try {
      return typeof logsJson === 'string' ? JSON.parse(logsJson) : logsJson
    } catch {
      return []
    }
  }, [logsJson])

  // 核心步骤合并算法：将同一步骤中连续的同名工具调用与结果合二为一
  const unifiedSteps: UnifiedStep[] = useMemo(() => {
    if (!mergeSteps) {
      // 原始视图模式：1:1 映射
      return rawSteps.map((st, i) => {
        const isTool = st.action === 'tool_call' || st.action === 'tool_result'
        const meta = ACTION_MAP[isTool ? 'tool' : st.action] || {
          label: st.action === 'tool_call' ? '调用工具' : (st.action === 'tool_result' ? '工具返回' : st.action),
          icon: isTool ? '⚡' : '•',
          badgeClass: 'step-badge-call',
        }
        return {
          id: `raw-${i}`,
          step: st.step,
          action: isTool ? 'tool' : (st.action as any),
          tool_name: st.tool_name,
          label: meta.label,
          icon: meta.icon,
          badgeClass: meta.badgeClass,
          timestamp: st.timestamp,
          thoughtContent: st.action === 'thought' ? st.output : undefined,
          operations: isTool ? [{
            input: st.input,
            output: st.output,
            isError: st.action === 'error',
            timestamp: st.timestamp,
          }] : [],
        }
      })
    }

    const merged: UnifiedStep[] = []
    let pendingToolOp: { step: number; tool_name: string; input?: string; timestamp: number } | null = null

    for (let i = 0; i < rawSteps.length; i++) {
      const st = rawSteps[i]

      if (st.action === 'thought') {
        merged.push({
          id: `thought-${i}-${st.step}`,
          step: st.step,
          action: 'thought',
          label: '思维分析',
          icon: '🧠',
          badgeClass: 'step-badge-thought',
          timestamp: st.timestamp,
          thoughtContent: st.output || '',
          operations: [],
        })
        continue
      }

      if (st.action === 'finish') {
        merged.push({
          id: `finish-${i}-${st.step}`,
          step: st.step,
          action: 'finish',
          label: '交付结论',
          icon: '✦',
          badgeClass: 'step-badge-finish',
          timestamp: st.timestamp,
          thoughtContent: st.output || '',
          operations: [],
        })
        continue
      }

      if (st.action === 'error' && !st.tool_name) {
        merged.push({
          id: `err-${i}-${st.step}`,
          step: st.step,
          action: 'error',
          label: '执行异常',
          icon: '⚠️',
          badgeClass: 'step-badge-error',
          timestamp: st.timestamp,
          thoughtContent: st.output || '',
          operations: [],
        })
        continue
      }

      if (st.action === 'tool_call') {
        pendingToolOp = {
          step: st.step,
          tool_name: st.tool_name || 'unknown_tool',
          input: st.input,
          timestamp: st.timestamp,
        }
        // 如果后面紧邻的不是 tool_result，直接作为一个独立调用记录
        const next = rawSteps[i + 1]
        if (!next || (next.action !== 'tool_result' && next.action !== 'error')) {
          appendOperation(merged, st.step, pendingToolOp.tool_name, {
            input: st.input,
            timestamp: st.timestamp,
          })
          pendingToolOp = null
        }
        continue
      }

      if (st.action === 'tool_result' || (st.action === 'error' && st.tool_name)) {
        const toolName = st.tool_name || pendingToolOp?.tool_name || 'tool'
        const inputVal = pendingToolOp && pendingToolOp.tool_name === toolName ? pendingToolOp.input : undefined
        appendOperation(merged, st.step, toolName, {
          input: inputVal,
          output: st.output,
          isError: st.action === 'error',
          timestamp: st.timestamp,
        })
        pendingToolOp = null
        continue
      }
    }

    return merged
  }, [rawSteps, mergeSteps])

  function appendOperation(
    list: UnifiedStep[],
    step: number,
    toolName: string,
    op: ToolOperation
  ) {
    const last = list[list.length - 1]
    // 检查末尾项是否为同一步骤内的同名工具
    if (last && last.action === 'tool' && last.step === step && last.tool_name === toolName) {
      last.operations.push(op)
    } else {
      list.push({
        id: `tool-${list.length}-${step}-${toolName}`,
        step,
        action: 'tool',
        tool_name: toolName,
        label: '调用工具',
        icon: '⚡',
        badgeClass: 'step-badge-call',
        timestamp: op.timestamp,
        operations: [op],
      })
    }
  }

  function toggle(id: string) {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  if (!rawSteps || rawSteps.length === 0) {
    return (
      <div className="log-empty">
        <span className="muted">暂无分步日志，任务执行时将实时流式记录思考与工具调用轨迹。</span>
      </div>
    )
  }

  const allIds = unifiedSteps.map((u) => u.id)
  const isAllExpanded = allIds.length > 0 && allIds.every((id) => expanded[id])

  return (
    <div className="timeline-wrap">
      <div className="timeline-head" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="timeline-title">
            规划与执行轨迹（共 {unifiedSteps.length} 个节点{mergeSteps && rawSteps.length > unifiedSteps.length ? `，已由 ${rawSteps.length} 项智能归集` : ''}）
          </span>
          <button
            className={`btn sm ${mergeSteps ? 'primary' : 'ghost'}`}
            style={{ padding: '3px 10px', fontSize: 12, borderRadius: 20 }}
            onClick={() => setMergeSteps(!mergeSteps)}
            title="将同一 Step 内重复的多次工具调用与结果卡片智能合并为一个整体"
          >
            {mergeSteps ? '✓ 已合并相同步骤' : '合并相同步骤'}
          </button>
        </div>

        <button
          className="btn ghost sm"
          onClick={() => {
            if (isAllExpanded) setExpanded({})
            else {
              const full: Record<string, boolean> = {}
              allIds.forEach((id) => (full[id] = true))
              setExpanded(full)
            }
          }}
        >
          {isAllExpanded ? '折叠全部' : '展开全部'}
        </button>
      </div>

      <div className="timeline">
        {unifiedSteps.map((st, idx) => {
          const isExp = expanded[st.id] ?? (st.action === 'finish' || st.action === 'error' || idx === unifiedSteps.length - 1)
          const timeStr = st.timestamp ? new Date(st.timestamp * 1000).toLocaleTimeString() : ''
          const opCount = st.operations.length

          // 收集多个子操作的简要对象信息
          const summaries = st.operations
            .map((op) => extractSummary(st.tool_name, op.input))
            .filter(Boolean)

          return (
            <div className={`timeline-item ${st.action}`} key={st.id}>
              <div className="timeline-marker">
                <span>{st.icon}</span>
              </div>
              <div className="timeline-card">
                <div className="timeline-header" onClick={() => toggle(st.id)}>
                  <div className="timeline-header-left" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                    <span className={`step-badge ${st.badgeClass}`}>{st.label}</span>
                    {st.tool_name && <span className="mono tool-pill" style={{ fontWeight: 600 }}>{st.tool_name}</span>}
                    {opCount > 1 && (
                      <span
                        className="badge"
                        style={{
                          background: 'rgba(79, 70, 229, 0.12)',
                          color: 'var(--accent, #4f46e5)',
                          border: '1px solid rgba(79, 70, 229, 0.25)',
                          borderRadius: 12,
                          padding: '2px 8px',
                          fontSize: 11,
                          fontWeight: 600,
                        }}
                      >
                        共 {opCount} 项操作合一
                      </span>
                    )}
                    <span className="step-num">Step {st.step}</span>

                    {/* 收起时且存在多项操作，展示微缩摘要预览 */}
                    {!isExp && summaries.length > 0 && (
                      <span
                        className="muted"
                        style={{
                          fontSize: 12,
                          maxWidth: 320,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          opacity: 0.85,
                        }}
                      >
                        [{summaries.slice(0, 3).join(', ')}{summaries.length > 3 ? '...' : ''}]
                      </span>
                    )}
                  </div>
                  <div className="timeline-header-right">
                    <span className="muted time-label">{timeStr}</span>
                    <span className="arrow-toggle">{isExp ? '▲' : '▼'}</span>
                  </div>
                </div>

                {isExp && (
                  <div className="timeline-content" style={{ marginTop: 8 }}>
                    {/* 思维分析 / 交付结论正文 */}
                    {st.thoughtContent && (
                      <div className="code-block-wrap">
                        <div className="code-label">{st.action === 'finish' ? '交付成果报告' : '深度思考与规划'}</div>
                        <pre className="code-block" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65 }}>
                          {st.thoughtContent}
                        </pre>
                      </div>
                    )}

                    {/* 单一工具操作 */}
                    {opCount === 1 && (
                      <>
                        {st.operations[0].input && (
                          <div className="code-block-wrap">
                            <div className="code-label">输入参数</div>
                            <pre className="code-block mono">{st.operations[0].input}</pre>
                          </div>
                        )}
                        {st.operations[0].output && (
                          <div className="code-block-wrap">
                            <div className="code-label">{st.operations[0].isError ? '异常详情' : '执行输出'}</div>
                            <pre className="code-block mono" style={{ color: st.operations[0].isError ? 'var(--red, #ef4444)' : undefined }}>
                              {st.operations[0].output}
                            </pre>
                          </div>
                        )}
                      </>
                    )}

                    {/* 多个相同步骤合并展示 */}
                    {opCount > 1 && (
                      <div className="sub-operations-list" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        <div className="muted" style={{ fontSize: 12, marginBottom: 2 }}>
                          已将本步骤内连续调用的 {opCount} 项 {st.tool_name} 操作归集如下：
                        </div>
                        {st.operations.map((op, opIdx) => {
                          const subSummary = extractSummary(st.tool_name, op.input)
                          return (
                            <div
                              key={opIdx}
                              style={{
                                background: 'var(--bg-1, rgba(0,0,0,0.03))',
                                border: '1px solid var(--border-color, rgba(0,0,0,0.08))',
                                borderRadius: 8,
                                padding: '10px 12px',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, fontSize: 12 }}>
                                <span style={{ fontWeight: 600, color: 'var(--accent, #4f46e5)' }}>
                                  #0{opIdx + 1} {subSummary ? `· ${subSummary}` : ''}
                                </span>
                                {op.isError && <span style={{ color: '#ef4444', fontWeight: 600 }}>失败</span>}
                              </div>
                              {op.input && (
                                <div style={{ marginBottom: 6 }}>
                                  <div className="muted" style={{ fontSize: 11, marginBottom: 2 }}>输入:</div>
                                  <pre className="code-block mono" style={{ margin: 0, padding: '6px 8px', fontSize: 11 }}>
                                    {op.input}
                                  </pre>
                                </div>
                              )}
                              {op.output && (
                                <div>
                                  <div className="muted" style={{ fontSize: 11, marginBottom: 2 }}>输出:</div>
                                  <pre
                                    className="code-block mono"
                                    style={{
                                      margin: 0,
                                      padding: '6px 8px',
                                      fontSize: 11,
                                      color: op.isError ? '#ef4444' : undefined,
                                      maxHeight: 180,
                                      overflowY: 'auto',
                                    }}
                                  >
                                    {op.output}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )
                        })}
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
