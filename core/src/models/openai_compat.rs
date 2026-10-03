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
    temperature: Option<f32>,
    client: reqwest::Client,
}

impl OpenAICompatProvider {
    pub fn new(name: String, base_url: String, model: String, api_key: Option<String>) -> Self {
        Self::with_options(name, base_url, model, api_key, None)
    }

    pub fn with_options(
        name: String,
        base_url: String,
        model: String,
        api_key: Option<String>,
        temperature: Option<f32>,
    ) -> Self {
        let client = reqwest::Client::builder()
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());
        Self { name, base_url: base_url.trim_end_matches('/').to_string(), model, api_key, client, temperature }
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
        let msgs: Vec<Value> = messages.iter().map(|m| message_to_value(m)).collect();

        let mut body = json!({
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens,
        });
        // Reasoning/thinking models reject sampling params in some modes, so only
        // emit temperature when a profile explicitly configured one.
        if let Some(t) = self.temperature {
            body["temperature"] = json!(t);
        }

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

        let resp = req.send().await?;
        let status = resp.status();
        if !status.is_success() {
            let text = resp.text().await.unwrap_or_default();
            let code = status.as_u16();
            let friendly_hint = match code {
                402 => "【API 账户余额不足】: 您当前配置的在线大模型 API Key 额度已耗尽。请在「设置 - 模型配置」中充值您的 API Key，或切换为其他在线提供商/启用本地内置离线大模型 (llama-server)。",
                401 => "【API 密钥未授权或无效】: 请检查「设置 - 模型配置」中的 API Key 是否填写正确或已过期。",
                429 => "【请求触发限流或超额】: API 调用频率已达到上游提供商限制，请稍候重试或调高额度。",
                500..=599 => "【模型上游服务器异常】: 服务商服务出现故障或超载，请稍候重试或切换备用模型。",
                _ => "模型请求失败",
            };
            return Err(AppError::Model(format!(
                "{friendly_hint} (HTTP {status}): {text}"
            )));
        }

        let v: Value = resp.json().await?;
        let choice = v
            .get("choices")
            .and_then(|c| c.get(0))
            .ok_or_else(|| AppError::Model("empty model response".into()))?;

        let message = choice.get("message");
        let content = message
            .and_then(|m| m.get("content"))
            .and_then(|c| c.as_str())
            .unwrap_or("")
            .to_string();

        let reasoning_content = message
            .and_then(|m| m.get("reasoning_content"))
            .and_then(|c| c.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_string());

        let tool_calls = message
            .and_then(|m| m.get("tool_calls"))
            .and_then(|tc| tc.as_array())
            .map(|arr| {
                arr.iter()
                    .enumerate()
                    .filter_map(|(idx, c)| {
                        let f = c.get("function")?;
                        let raw_args = f.get("arguments")?.as_str().unwrap_or("");
                        let arguments = if raw_args.trim().is_empty() {
                            serde_json::json!({})
                        } else {
                            serde_json::from_str::<Value>(raw_args).unwrap_or(Value::Null)
                        };
                        // 有些本地模型（llama.cpp）不返回 id；空 tool_call_id 会被
                        // 服务端判为非法，这里合成一个稳定 id 保证成对出现。
                        let id = c
                            .get("id")
                            .and_then(|v| v.as_str())
                            .filter(|s| !s.is_empty())
                            .map(|s| s.to_string())
                            .unwrap_or_else(|| format!("call_{idx}"));
                        Some(ToolCall {
                            id,
                            name: f.get("name")?.as_str()?.to_string(),
                            arguments,
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
        Ok(ModelResponse { content, tool_calls, finish_reason, reasoning_content })
    }
}



fn message_to_value(m: &ChatMessage) -> Value {
    let mut obj = json!({ "role": m.role, "content": m.content });
    if let Some(tc) = &m.tool_calls {
        obj["tool_calls"] = json!(tc
            .iter()
            .map(|c| json!({
                "id": c.id,
                "type": "function",
                "function": {
                    "name": c.name,
                    "arguments": match &c.arguments {
                        Value::String(s) => s.clone(),
                        other => serde_json::to_string(other).unwrap_or_else(|_| "{}".into()),
                    }
                }
            }))
            .collect::<Vec<_>>());
    }
    if let Some(id) = &m.tool_call_id {
        obj["tool_call_id"] = json!(id);
    }
    if let Some(rc) = &m.reasoning_content {
        obj["reasoning_content"] = json!(rc);
    }
    obj
}

