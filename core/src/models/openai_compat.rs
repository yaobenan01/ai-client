use super::{ChatMessage, ModelProvider, ModelResponse, ToolCall, ToolSpec};
use crate::error::{AppError, Result};
use async_trait::async_trait;
use serde_json::{json, Value};

/// OpenAI-compatible `/chat/completions` client.
///
/// Used both for local llama.cpp `llama-server` (local_gguf) and for any
/// OpenAI-compatible local endpoint (openai_compat). No network dependency
/// when pointed at a localhost server.
pub struct OpenAICompatProvider {
    name: String,
    base_url: String,
    model: String,
    api_key: Option<String>,
    client: reqwest::Client,
}

impl OpenAICompatProvider {
    pub fn new(name: String, base_url: String, model: String, api_key: Option<String>) -> Self {
        let client = reqwest::Client::builder()
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());
        Self { name, base_url: base_url.trim_end_matches('/').to_string(), model, api_key, client }
    }
}

#[async_trait]
impl ModelProvider for OpenAICompatProvider {
    fn name(&self) -> &str {
        &self.name
    }

    async fn chat(
        &self,
        messages: &[ChatMessage],
        tools: &[ToolSpec],
        max_tokens: u32,
    ) -> Result<ModelResponse> {
        let url = format!("{}/chat/completions", self.base_url);
        let msgs: Vec<Value> = messages
            .iter()
            .map(|m| json!({ "role": m.role, "content": m.content }))
            .collect();

        let mut body = json!({
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        });

        if !tools.is_empty() {
            body["tools"] = json!(tools
                .iter()
                .map(|t| json!({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters
                    }
                }))
                .collect::<Vec<_>>());
        }

        let mut req = self.client.post(&url).json(&body);
        if let Some(key) = &self.api_key {
            req = req.bearer_auth(key);
        }

        let resp = req.send().await?.error_for_status()?;
        let v: Value = resp.json().await?;
        let choice = v
            .get("choices")
            .and_then(|c| c.get(0))
            .ok_or_else(|| AppError::Model("empty model response".into()))?;

        let content = choice
            .get("message")
            .and_then(|m| m.get("content"))
            .and_then(|c| c.as_str())
            .unwrap_or("")
            .to_string();

        let tool_calls = choice
            .get("message")
            .and_then(|m| m.get("tool_calls"))
            .and_then(|tc| tc.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|c| {
                        let f = c.get("function")?;
                        Some(ToolCall {
                            name: f.get("name")?.as_str()?.to_string(),
                            arguments: serde_json::from_str(f.get("arguments")?.as_str()?)
                                .unwrap_or(Value::Null),
                        })
                    })
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default();

        let finish_reason = choice
            .get("finish_reason")
            .and_then(|f| f.as_str())
            .unwrap_or("stop")
            .to_string();

        Ok(ModelResponse { content, tool_calls, finish_reason })
    }
}
