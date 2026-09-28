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
    pub logs: Option<String>,
    pub artifacts: Option<String>,
    pub model_id: Option<String>,
    pub created_at: Option<i64>,
    pub updated_at: Option<i64>,
}

impl Task {
    pub fn status(&self) -> TaskStatus {
        TaskStatus::from_str(&self.status)
    }
}

/// A structured step in an agent run for observability and timeline visualization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskStep {
    pub step: usize,
    pub action: String, // "thought", "tool_call", "tool_result", "finish", "error"
    pub tool_name: Option<String>,
    pub input: Option<String>,
    pub output: Option<String>,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentRunOutput {
    pub final_answer: String,
    pub steps: Vec<TaskStep>,
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
        let output = self.run_with_reporter(ctx, task_input, |_, _| {}).await?;
        Ok(output.final_answer)
    }

    /// Run a task while streaming each step to a reporter callback.
    pub async fn run_with_reporter<F>(
        &self,
        ctx: &ToolContext,
        task_input: &str,
        mut reporter: F,
    ) -> Result<AgentRunOutput>
    where
        F: FnMut(usize, &TaskStep) + Send,
    {
        let mut messages: Vec<ChatMessage> = vec![
            ChatMessage { role: "system".into(), content: self.config.system_prompt.clone() },
            ChatMessage { role: "user".into(), content: task_input.to_string() },
        ];

        let specs = self.tools.specs();
        let mut final_answer = String::new();
        let mut steps = Vec::new();

        for step in 0..self.config.max_iterations {
            // Context Management: trim history to respect sliding window token budget
            let trimmed_messages = crate::context::trim_history(messages.clone(), 16);

            let resp = self.provider.chat(&trimmed_messages, &specs, self.config.max_tokens).await?;
            final_answer = resp.content.clone();

            // Record thought if content is non-empty
            if !resp.content.trim().is_empty() {
                let thought_step = TaskStep {
                    step: step + 1,
                    action: "thought".into(),
                    tool_name: None,
                    input: None,
                    output: Some(resp.content.clone()),
                    timestamp: chrono::Utc::now().timestamp(),
                };
                steps.push(thought_step.clone());
                reporter(step + 1, &thought_step);
            }

            // CRITICAL FIX: Only treat as final answer if NO tool calls were returned.
            // Some models return finish_reason="stop" even with tool_calls.
            if resp.tool_calls.is_empty() {
                messages.push(ChatMessage { role: "assistant".into(), content: resp.content.clone() });
                let finish_step = TaskStep {
                    step: step + 1,
                    action: "finish".into(),
                    tool_name: None,
                    input: None,
                    output: Some(resp.content.clone()),
                    timestamp: chrono::Utc::now().timestamp(),
                };
                steps.push(finish_step.clone());
                reporter(step + 1, &finish_step);
                break;
            }

            // Record the assistant turn with tool calls, then execute each requested tool.
            let mut assistant_turn = resp.content.clone();
            for call in &resp.tool_calls {
                assistant_turn.push_str(&format!("\n[tool] {} {}\n", call.name, call.arguments));
            }
            messages.push(ChatMessage { role: "assistant".into(), content: assistant_turn });

            for call in &resp.tool_calls {
                let call_step = TaskStep {
                    step: step + 1,
                    action: "tool_call".into(),
                    tool_name: Some(call.name.clone()),
                    input: Some(call.arguments.to_string()),
                    output: None,
                    timestamp: chrono::Utc::now().timestamp(),
                };
                steps.push(call_step.clone());
                reporter(step + 1, &call_step);

                let output = self.dispatch(&call.name, call.arguments.clone(), ctx).await;
                let obs = format_tool_observation(&call.name, output.clone());

                let result_step = TaskStep {
                    step: step + 1,
                    action: if output.error.is_some() { "error".into() } else { "tool_result".into() },
                    tool_name: Some(call.name.clone()),
                    input: None,
                    output: Some(obs.clone()),
                    timestamp: chrono::Utc::now().timestamp(),
                };
                steps.push(result_step.clone());
                reporter(step + 1, &result_step);

                messages.push(ChatMessage { role: "tool".into(), content: obs });
            }
        }

        Ok(AgentRunOutput { final_answer, steps })
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
