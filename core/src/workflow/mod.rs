use crate::error::Result;
use crate::models::{ChatMessage, ModelProvider};
use crate::tools::{ToolContext, ToolRegistry};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::sync::Arc;

/// A user-defined business workflow ("业务逻辑执行").
///
/// Steps run sequentially for the scaffold; loop/parallel/branch primitives are
/// added on top of the same executor. Each step is either an LLM prompt or a
/// tool invocation, and step outputs are passed forward via `{{variables}}`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowDef {
    pub id: String,
    pub name: String,
    pub steps: Vec<WorkflowStep>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStep {
    pub kind: String, // "llm" | "tool"
    pub prompt: Option<String>,
    pub tool: Option<String>,
    pub args: Option<Value>,
}

pub struct WorkflowEngine {
    provider: Arc<dyn ModelProvider>,
    tools: Arc<ToolRegistry>,
}

impl WorkflowEngine {
    pub fn new(provider: Arc<dyn ModelProvider>, tools: Arc<ToolRegistry>) -> Self {
        Self { provider, tools }
    }

    pub async fn run(&self, def: &WorkflowDef, input: &str, ctx: &ToolContext) -> Result<Value> {
        let mut vars: HashMap<String, String> = HashMap::new();
        vars.insert("input".into(), input.to_string());
        let mut last: Value = Value::String(input.to_string());

        for step in &def.steps {
            match step.kind.as_str() {
                "llm" => {
                    let prompt = render(&step.prompt.clone().unwrap_or_default(), &vars);
                    let resp = self
                        .provider
                        .chat(&[ChatMessage { role: "user".into(), content: prompt, ..Default::default() }], &[], 2048)
                        .await?;
                    last = Value::String(resp.content.clone());
                    vars.insert("last".into(), resp.content);
                }
                "tool" => {
                    let tool_name = step.tool.clone().unwrap_or_default();
                    let args = step.args.clone().unwrap_or(Value::Null);
                    let out = match self.tools.get(&tool_name) {
                        Some(t) => t.run(args, ctx).await?,
                        None => return Err(crate::error::AppError::Tool(format!("未知工具 {tool_name}"))),
                    };
                    last = serde_json::json!({ "content": out.content, "error": out.error });
                    vars.insert("last".into(), serde_json::to_string(&last)?);
                }
                other => {
                    return Err(crate::error::AppError::Workflow(format!("未知步骤类型 {other}")));
                }
            }
        }
        Ok(last)
    }
}

/// Minimal `{{var}}` substitution for step prompts.
fn render(template: &str, vars: &HashMap<String, String>) -> String {
    let mut out = template.to_string();
    for (k, v) in vars {
        out = out.replace(&format!("{{{{{k}}}}}"), v);
    }
    out
}



