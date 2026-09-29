use crate::error::Result;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

pub mod llama_cpp;
pub mod openai_compat;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
    /// Structured tool-call payload emitted by the assistant (OpenAI format).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_calls: Option<Vec<ToolCall>>,
    /// Correlation id for a `tool` role message answering an assistant tool call.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_call_id: Option<String>,
    /// Reasoning trace that thinking models require to be echoed back.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reasoning_content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolSpec {
    pub name: String,
    pub description: String,
    pub parameters: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ToolCall {
    pub name: String,
    pub arguments: serde_json::Value,
    /// Provider-assigned call id (required to answer tool calls in OpenAI format).
    #[serde(default)]
    pub id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ModelResponse {
    pub content: String,
    pub tool_calls: Vec<ToolCall>,
    pub finish_reason: String,
    /// Reasoning trace returned by thinking models; must be echoed on next turn.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reasoning_content: Option<String>,
}

#[async_trait]
pub trait ModelProvider: Send + Sync {
    fn name(&self) -> &str;
    async fn chat(
        &self,
        messages: &[ChatMessage],
        tools: &[ToolSpec],
        max_tokens: u32,
    ) -> Result<ModelResponse>;
}

pub type Provider = Arc<dyn ModelProvider>;

/// A persisted model configuration ("大模型配置").
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelProfile {
    pub id: String,
    pub name: String,
    /// `openai_compat` | `local_gguf` | `local_onnx` | `remote`
    pub kind: String,
    pub config: serde_json::Value,
}

impl ModelProfile {
    pub fn build(&self) -> Result<Provider> {
        match self.kind.as_str() {
            "openai_compat" | "local_gguf" => {
                let base_url = self
                    .config
                    .get("base_url")
                    .and_then(|v| v.as_str())
                    .unwrap_or("http://127.0.0.1:8080/v1")
                    .to_string();
                let model = self
                    .config
                    .get("model")
                    .and_then(|v| v.as_str())
                    .unwrap_or("local")
                    .to_string();
                let api_key = self.config.get("api_key").and_then(|v| v.as_str()).map(|s| s.to_string());
                let temperature = self
                    .config
                    .get("temperature")
                    .and_then(|v| v.as_f64())
                    .map(|t| t as f32);
                Ok(Arc::new(openai_compat::OpenAICompatProvider::with_options(
                    self.name.clone(),
                    base_url,
                    model,
                    api_key,
                    temperature,
                )))
            }
            other => Err(crate::error::AppError::Model(format!("unsupported model kind: {other}"))),
        }
    }
}

#[derive(Default)]
pub struct ModelRegistry {
    profiles: RwLock<HashMap<String, ModelProfile>>,
    default: RwLock<Option<String>>,
}

impl ModelRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add(&self, profile: ModelProfile) {
        self.profiles.write().unwrap().insert(profile.id.clone(), profile);
    }

    pub fn remove(&self, id: &str) {
        self.profiles.write().unwrap().remove(id);
    }

    pub fn get(&self, id: &str) -> Option<ModelProfile> {
        self.profiles.read().unwrap().get(id).cloned()
    }

    pub fn list(&self) -> Vec<ModelProfile> {
        let mut v: Vec<_> = self.profiles.read().unwrap().values().cloned().collect();
        v.sort_by(|a, b| a.name.cmp(&b.name));
        v
    }

    pub fn set_default(&self, id: Option<String>) {
        *self.default.write().unwrap() = id;
    }

    pub fn default_id(&self) -> Option<String> {
        self.default.read().unwrap().clone()
    }

    pub fn resolve(&self, id: Option<&str>) -> Option<ModelProfile> {
        match id {
            Some(id) => self.get(id),
            None => self.default_id().and_then(|d| self.get(&d)),
        }
    }
}




