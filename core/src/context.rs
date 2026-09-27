use crate::models::ChatMessage;

/// Assembles and trims the prompt context ("上下文管理").
///
/// For the scaffold this implements a sliding window: it keeps the system
/// prompt plus the most recent messages under a rough token budget.
/// Production will layer on: summarization and local embedding based
/// retrieval (RAG memory).
pub fn trim_history(mut messages: Vec<ChatMessage>, max_messages: usize) -> Vec<ChatMessage> {
    let system_count = messages.iter().take_while(|m| m.role == "system").count();
    let tail = messages.split_off(system_count);
    let keep = tail.len().min(max_messages);
    let start = tail.len() - keep;
    messages.extend(tail.into_iter().skip(start));
    messages
}

/// Estimate token count as `ceil(chars / 3)` (rough CJK-aware heuristic).
pub fn estimate_tokens(text: &str) -> usize {
    (text.chars().count() + 2) / 3
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trims_history_keeps_system() {
        let msgs = vec![
            ChatMessage { role: "system".into(), content: "s".into() },
            ChatMessage { role: "user".into(), content: "1".into() },
            ChatMessage { role: "user".into(), content: "2".into() },
            ChatMessage { role: "user".into(), content: "3".into() },
        ];
        let t = trim_history(msgs, 2);
        assert_eq!(t.len(), 3); // system + last 2 user messages
        assert_eq!(t[0].role, "system");
        assert_eq!(t[1].content, "2");
        assert_eq!(t[2].content, "3");
    }

    #[test]
    fn estimate_tokens_is_positive() {
        assert!(estimate_tokens("你好，世界") >= 2);
    }
}
