use crate::error::Result;
use crate::models::{ChatMessage, ModelProvider, ModelResponse};
use crate::tools::{ToolContext, ToolOutput, ToolRegistry};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskStatus {
    Pending,
    Planning,
    Running,
    AwaitingInput,
    Done,
    Failed,
    Cancelled,
}

impl TaskStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            TaskStatus::Pending => "pending",
            TaskStatus::Planning => "planning",
            TaskStatus::Running => "running",
            TaskStatus::AwaitingInput => "awaiting_input",
            TaskStatus::Done => "done",
            TaskStatus::Failed => "failed",
            TaskStatus::Cancelled => "cancelled",
        }
    }

    pub fn from_str(s: &str) -> Self {
        match s {
            "planning" => TaskStatus::Planning,
            "running" => TaskStatus::Running,
            "awaiting_input" => TaskStatus::AwaitingInput,
            "done" => TaskStatus::Done,
            "failed" => TaskStatus::Failed,
            "cancelled" => TaskStatus::Cancelled,
            _ => TaskStatus::Pending,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub title: String,
    pub input: String,
    pub status: String,
    pub progress: i64,
    pub result: Option<String>,
}

impl Task {
    pub fn status(&self) -> TaskStatus {
        TaskStatus::from_str(&self.status)
    }
}

#[derive(Debug, Clone)]
pub struct AgentConfig {
    pub system_prompt: String,
    pub max_iterations: usize,
    pub max_tokens: u32,
    pub allow_commands: bool,
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            system_prompt: "你是一个离线 AI 智能体，请使用可用工具完成任务，最终用中文给出结论。".into(),
            max_iterations: 24,
            max_tokens: 2048,
            allow_commands: true,
        }
    }
}

/// The core execution algorithm ("核心执行算法").
///
/// Implements a plan → act → observe → reflect loop inspired by codex /
/// Doubao-style agents. It is model-agnostic through `ModelProvider` and
/// tool-agnostic through `ToolRegistry`.
pub struct Agent {
    provider: Arc<dyn ModelProvider>,
    tools: Arc<ToolRegistry>,
    config: AgentConfig,
}

impl Agent {
    pub fn new(provider: Arc<dyn ModelProvider>, tools: Arc<ToolRegistry>, config: AgentConfig) -> Self {
        Self { provider, tools, config }
    }

    /// Run a task to completion and return the final answer.
    pub async fn run(&self, ctx: &ToolContext, task_input: &str) -> Result<String> {
        let mut messages: Vec<ChatMessage> = vec![
            ChatMessage { role: "system".into(), content: self.config.system_prompt.clone() },
            ChatMessage { role: "user".into(), content: task_input.to_string() },
        ];

        let specs = self.tools.specs();
        let mut final_answer = String::new();

        for _step in 0..self.config.max_iterations {
            let resp = self.provider.chat(&messages, &specs, self.config.max_tokens).await?;
            final_answer = resp.content.clone();

            // No tool calls => the model produced its final answer.
            if resp.tool_calls.is_empty() || resp.finish_reason == "stop" {
                messages.push(ChatMessage { role: "assistant".into(), content: resp.content.clone() });
                break;
            }

            // Record the assistant turn, then execute each requested tool.
            let mut assistant_turn = resp.content.clone();
            for call in &resp.tool_calls {
                assistant_turn.push_str(&format!("\n[tool] {} {}\n", call.name, call.arguments));
            }
            messages.push(ChatMessage { role: "assistant".into(), content: assistant_turn });

            for call in &resp.tool_calls {
                let output = self.dispatch(&call.name, call.arguments.clone(), ctx).await;
                let obs = format_tool_observation(&call.name, output);
                // TODO(tool-protocol): emit role "tool" + tool_call_id for strict
                // OpenAI compatibility once ChatMessage carries call ids.
                messages.push(ChatMessage { role: "tool".into(), content: obs });
            }
        }

        Ok(final_answer)
    }

    async fn dispatch(&self, name: &str, args: serde_json::Value, ctx: &ToolContext) -> ToolOutput {
        match self.tools.get(name) {
            Some(tool) => match tool.run(args, ctx).await {
                Ok(out) => out,
                Err(e) => ToolOutput::err(e.to_string()),
            },
            None => ToolOutput::err(format!("未知工具: {name}")),
        }
    }
}

fn format_tool_observation(name: &str, out: ToolOutput) -> String {
    if let Some(err) = out.error {
        format!("工具 {name} 执行出错: {err}")
    } else {
        format!("工具 {name} 返回: {}", out.content)
    }
}

/// Convenience for tests / one-off calls.
#[allow(dead_code)]
pub fn blank_response() -> ModelResponse {
    ModelResponse::default()
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_roundtrip() {
        assert_eq!(TaskStatus::from_str("done"), TaskStatus::Done);
        assert_eq!(TaskStatus::from_str("running"), TaskStatus::Running);
        assert_eq!(TaskStatus::from_str("unknown"), TaskStatus::Pending);
        assert_eq!(TaskStatus::Running.as_str(), "running");
    }

    #[test]
    fn tool_observation_formats_errors() {
        let ok = format_tool_observation("t", ToolOutput::ok("yes"));
        assert!(ok.contains("yes"));
        let err = format_tool_observation("t", ToolOutput::err("boom"));
        assert!(err.contains("boom"));
    }
}
