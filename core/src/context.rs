use crate::models::ChatMessage;

/// Assembles and trims the prompt context ("上下文管理").
///
/// 两点硬约束：
/// 1. 裁剪结果必须仍是**合法的工具调用序列**。OpenAI/DeepSeek 要求 `role=tool`
///    必须紧跟在带 `tool_calls` 的 assistant 之后；纯按条数滑动窗口会把该
///    assistant 切掉、只留下 tool 结果，服务端直接 400：
///    `Messages with role 'tool' must be a response to a preceding message with 'tool_calls'`。
/// 2. 最初那条 user 任务描述要一直保留，否则长任务会把目标丢掉。
///
/// 生产环境可在此之上叠加摘要与本地向量检索（RAG 记忆）。
pub fn trim_history(messages: Vec<ChatMessage>, max_messages: usize) -> Vec<ChatMessage> {
    let system_count = messages.iter().take_while(|m| m.role == "system").count();
    let mut out: Vec<ChatMessage> = messages[..system_count].to_vec();

    let rest = &messages[system_count..];

    // 固定头部：保留最初的用户任务描述。
    let (anchor, tail): (Option<&ChatMessage>, &[ChatMessage]) =
        match rest.iter().position(|m| m.role == "user") {
            Some(i) => (Some(&rest[i]), &rest[i + 1..]),
            None => (None, rest),
        };
    if let Some(a) = anchor {
        out.push(a.clone());
    }

    if tail.len() <= max_messages {
        out.extend_from_slice(tail);
        return out;
    }

    // 先按条数切出最近的窗口。
    let mut start = tail.len() - max_messages;

    // 修正 1：窗口不能以 tool 结果开头 —— 向前扩展，把发出 tool_calls 的
    // assistant 一并包含进来（并行工具调用会产生连续多条 tool 消息）。
    while start > 0 && tail[start].role == "tool" {
        start -= 1;
    }

    let mut kept: Vec<ChatMessage> = tail[start..].to_vec();

    // 修正 2：兜底。若历史本身不完整（开头就是孤立 tool），直接丢弃这些消息，
    // 宁可在本轮少给模型一点观察结果，也不能让整个请求 400 失败。
    while kept.first().map(|m| m.role.as_str()) == Some("tool") {
        kept.remove(0);
    }

    out.extend(kept);
    out
}

/// Estimate token count as `ceil(chars / 3)` (rough CJK-aware heuristic).
pub fn estimate_tokens(text: &str) -> usize {
    (text.chars().count() + 2) / 3
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::ToolCall;

    fn msg(role: &str, content: &str) -> ChatMessage {
        ChatMessage { role: role.into(), content: content.into(), ..Default::default() }
    }

    fn assistant_with_call(id: &str) -> ChatMessage {
        ChatMessage {
            role: "assistant".into(),
            content: String::new(),
            tool_calls: Some(vec![ToolCall {
                id: id.into(),
                name: "list_dir".into(),
                arguments: serde_json::json!({}),
            }]),
            ..Default::default()
        }
    }

    fn tool_result(id: &str) -> ChatMessage {
        ChatMessage {
            role: "tool".into(),
            content: "ok".into(),
            tool_call_id: Some(id.into()),
            ..Default::default()
        }
    }

    #[test]
    fn trims_history_keeps_system_and_original_task() {
        let msgs = vec![
            msg("system", "s"),
            msg("user", "task"),
            msg("user", "2"),
            msg("user", "3"),
        ];
        let t = trim_history(msgs, 2);
        assert_eq!(t[0].role, "system");
        // 最初的用户任务被固定保留
        assert_eq!(t[1].content, "task");
        assert_eq!(t.last().unwrap().content, "3");
    }

    #[test]
    fn trimmed_window_never_orphans_tool_messages() {
        let mut msgs = vec![msg("system", "s"), msg("user", "task")];
        for i in 0..10 {
            msgs.push(assistant_with_call(&format!("c{i}")));
            msgs.push(tool_result(&format!("c{i}")));
        }

        // 用各种窗口大小裁剪，结果都必须是合法的工具调用序列。
        for window in [1usize, 2, 3, 4, 5, 7, 16] {
            let t = trim_history(msgs.clone(), window);
            assert_eq!(t[0].role, "system");
            let mut seen_calls = false;
            for m in &t {
                match m.role.as_str() {
                    "assistant" => seen_calls = m.tool_calls.is_some(),
                    "tool" => assert!(
                        seen_calls,
                        "工具结果前必须存在 assistant(tool_calls)，window={window}"
                    ),
                    _ => {}
                }
            }
        }
    }

    #[test]
    fn estimate_tokens_is_positive() {
        assert!(estimate_tokens("你好，世界") >= 2);
    }
}
