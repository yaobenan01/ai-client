use super::{Tool, ToolContext, ToolOutput};
use crate::error::{AppError, Result};
use crate::models::ToolSpec;
use async_trait::async_trait;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

fn arg<'a>(args: &'a Value, key: &str) -> Result<&'a str> {
    args.get(key)
        .and_then(|v| v.as_str())
        .ok_or_else(|| AppError::Tool(format!("missing string arg: {key}")))
}

/// Resolve a path inside the workspace and keep it within the workspace root.
fn resolve_in_workspace(workspace: &Path, raw: &str) -> Result<PathBuf> {
    let base = workspace.canonicalize().unwrap_or_else(|_| workspace.to_path_buf());
    let joined = if Path::new(raw).is_absolute() {
        PathBuf::from(raw)
    } else {
        base.join(raw)
    };
    let normalized = joined.canonicalize().unwrap_or(joined);
    if !normalized.starts_with(&base) {
        return Err(AppError::Tool(format!("路径越界：{raw}")));
    }
    Ok(normalized)
}

pub struct ReadFile;

#[async_trait]
impl Tool for ReadFile {
    fn name(&self) -> &str {
        "read_file"
    }
    fn spec(&self) -> ToolSpec {
        ToolSpec {
            name: "read_file".into(),
            description: "读取工作区内文本文件内容".into(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string", "description": "相对或绝对路径" } },
                "required": ["path"]
            }),
        }
    }
    async fn run(&self, args: Value, ctx: &ToolContext) -> Result<ToolOutput> {
        let path = resolve_in_workspace(&ctx.workspace_dir, arg(&args, "path")?)?;
        let meta = std::fs::metadata(&path).map_err(|e| AppError::Tool(format!("读取失败 {path:?}: {e}")))?;
        if meta.len() > 2 * 1024 * 1024 {
            return Ok(ToolOutput::err("文件过大（>2MB），请分段读取"));
        }
        let content = std::fs::read_to_string(&path).map_err(|e| AppError::Tool(e.to_string()))?;
        Ok(ToolOutput::ok(content))
    }
}

pub struct WriteFile;

#[async_trait]
impl Tool for WriteFile {
    fn name(&self) -> &str {
        "write_file"
    }
    fn spec(&self) -> ToolSpec {
        ToolSpec {
            name: "write_file".into(),
            description: "将内容写入工作区内文件".into(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "path": { "type": "string" },
                    "content": { "type": "string" }
                },
                "required": ["path", "content"]
            }),
        }
    }
    async fn run(&self, args: Value, ctx: &ToolContext) -> Result<ToolOutput> {
        let path = resolve_in_workspace(&ctx.workspace_dir, arg(&args, "path")?)?;
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| AppError::Tool(e.to_string()))?;
        }
        let content = arg(&args, "content")?;
        std::fs::write(&path, content).map_err(|e| AppError::Tool(e.to_string()))?;
        Ok(ToolOutput::ok(format!("已写入 {}", path.display())))
    }
}

pub struct ListDir;

#[async_trait]
impl Tool for ListDir {
    fn name(&self) -> &str {
        "list_dir"
    }
    fn spec(&self) -> ToolSpec {
        ToolSpec {
            name: "list_dir".into(),
            description: "列出工作区内目录内容".into(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string", "description": "目录，默认工作区根" } }
            }),
        }
    }
    async fn run(&self, args: Value, ctx: &ToolContext) -> Result<ToolOutput> {
        let raw = args.get("path").and_then(|v| v.as_str()).unwrap_or(".");
        let path = resolve_in_workspace(&ctx.workspace_dir, raw)?;
        let entries = std::fs::read_dir(&path).map_err(|e| AppError::Tool(e.to_string()))?;
        let mut out = String::new();
        for e in entries.flatten() {
            let name = e.file_name().to_string_lossy().to_string();
            let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
            out.push_str(if is_dir { &format!("[dir]  {name}\n") } else { &format!("[file] {name}\n") });
        }
        Ok(ToolOutput::ok(out))
    }
}

pub struct RunCommand;

#[async_trait]
impl Tool for RunCommand {
    fn name(&self) -> &str {
        "run_command"
    }
    fn spec(&self) -> ToolSpec {
        ToolSpec {
            name: "run_command".into(),
            description: "在工作区执行系统命令（受白名单与开关限制）".into(),
            parameters: json!({
                "type": "object",
                "properties": { "command": { "type": "string" } },
                "required": ["command"]
            }),
        }
    }
    async fn run(&self, args: Value, ctx: &ToolContext) -> Result<ToolOutput> {
        if !ctx.allow_commands {
            return Ok(ToolOutput::err("命令执行未开启（allow_commands=false）"));
        }
        let cmd = arg(&args, "command")?;
        let (shell, flag) = if cfg!(windows) { ("cmd", "/C") } else { ("sh", "-c") };
        let output = std::process::Command::new(shell)
            .arg(flag)
            .arg(cmd)
            .current_dir(&ctx.workspace_dir)
            .output()
            .map_err(|e| AppError::Tool(e.to_string()))?;
        let mut text = String::from_utf8_lossy(&output.stdout).to_string();
        text.push_str(&String::from_utf8_lossy(&output.stderr));
        if output.status.success() {
            Ok(ToolOutput::ok(text))
        } else {
            Ok(ToolOutput::err(format!("exit={:?}\n{text}", output.status.code())))
        }
    }
}
