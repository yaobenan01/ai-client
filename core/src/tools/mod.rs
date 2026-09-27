use crate::error::Result;
use crate::models::ToolSpec;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;

pub mod builtin;

#[derive(Debug, Clone)]
pub struct ToolContext {
    pub workspace_dir: PathBuf,
    pub allow_commands: bool,
    pub command_whitelist: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolOutput {
    pub content: String,
    pub error: Option<String>,
}

impl ToolOutput {
    pub fn ok(content: impl Into<String>) -> Self {
        Self { content: content.into(), error: None }
    }
    pub fn err(e: impl Into<String>) -> Self {
        Self { content: String::new(), error: Some(e.into()) }
    }
}

#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn spec(&self) -> ToolSpec;
    async fn run(&self, args: Value, ctx: &ToolContext) -> Result<ToolOutput>;
}

pub type SharedTool = Arc<dyn Tool>;

#[derive(Default)]
pub struct ToolRegistry {
    tools: HashMap<String, SharedTool>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register<T: Tool + 'static>(&mut self, tool: T) {
        self.tools.insert(tool.name().to_string(), Arc::new(tool));
    }

    pub fn get(&self, name: &str) -> Option<SharedTool> {
        self.tools.get(name).cloned()
    }

    pub fn specs(&self) -> Vec<ToolSpec> {
        self.tools.values().map(|t| t.spec()).collect()
    }

    pub fn names(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }
}

/// Registry pre-populated with built-in tools.
pub fn default_registry() -> ToolRegistry {
    let mut r = ToolRegistry::new();
    r.register(builtin::ReadFile);
    r.register(builtin::WriteFile);
    r.register(builtin::ListDir);
    r.register(builtin::RunCommand);
    r
}
