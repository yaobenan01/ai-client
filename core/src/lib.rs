pub mod agent;
pub mod auth;
pub mod config;
pub mod context;
pub mod error;
pub mod models;
pub mod plugins;
pub mod ppt;
pub mod server;
pub mod storage;
pub mod tools;
pub mod workflow;

use crate::agent::{Agent, AgentConfig, Task, TaskStatus};
use crate::auth::{AuthService, Session, User};
use crate::config::AppConfig;
use crate::error::Result;
use crate::models::llama_cpp::LlamaServerManager;
use crate::models::{ModelProfile, ModelRegistry, Provider};
use crate::plugins::PluginManager;
use crate::ppt::{PptRuntime, PptRuntimeConfig};
use crate::storage::Db;
use crate::tools::{default_registry, ToolContext, ToolRegistry};
use rusqlite::{params, OptionalExtension};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use uuid::Uuid;

/// Top-level application state wiring all subsystems together.
pub struct Core {
    pub config: AppConfig,
    pub db: Db,
    pub auth: AuthService,
    pub models: Arc<ModelRegistry>,
    pub tools: Arc<ToolRegistry>,
    pub plugins: PluginManager,
    pub ppt: PptRuntime,
    pub llama: Arc<LlamaServerManager>,
}

impl Core {
    /// Initialize the core: open DB, apply schema, load persisted state.
    pub fn init(config: AppConfig) -> Result<Self> {
        let db = Db::open(&config.db_path())?;
        let auth = AuthService::new(db.clone());
        let models = Arc::new(ModelRegistry::new());
        load_model_profiles(&db, &models)?;

        let tools = Arc::new(default_registry());
        let plugins = PluginManager::new(config.plugins_dir.clone());
        let ppt = PptRuntime::detect(PptRuntimeConfig {
            ppt_master_dir: Some(config.plugins_dir.join("ppt-master")),
            tts_engine: "cosyvoice".into(),
            ..Default::default()
        })?;

        let llama_bin = config
            .llama_server_bin
            .clone()
            .or_else(|| std::env::var_os("AI_CLIENT_LLAMA_SERVER").map(PathBuf::from))
            .unwrap_or_else(|| PathBuf::from(if cfg!(windows) { "llama-server.exe" } else { "llama-server" }));
        let llama = Arc::new(LlamaServerManager::new(llama_bin));

        Ok(Self { config, db, auth, models, tools, plugins, ppt, llama })
    }

    // ---- auth ----
    pub fn register(&self, username: &str, password: &str) -> Result<User> {
        self.auth.register(username, password)
    }

    pub fn login(&self, username: &str, password: &str) -> Result<Session> {
        self.auth.login(username, password)
    }

    pub fn verify_session(&self, token: &str) -> Result<User> {
        self.auth.verify_session(token)
    }

    pub fn logout(&self, token: &str) -> Result<()> {
        self.auth.logout(token)
    }

    // ---- models ----
    pub fn list_models(&self) -> Vec<ModelProfile> {
        self.models.list()
    }

    pub fn add_model(&self, mut profile: ModelProfile) -> Result<ModelProfile> {
        if profile.id.is_empty() {
            profile.id = Uuid::new_v4().to_string();
        }
        let now = chrono::Utc::now().timestamp();
        let is_default = if Some(&profile.id) == self.models.default_id().as_ref() { 1 } else { 0 };
        let config_json = serde_json::to_string(&profile.config)?;
        self.db.conn().execute(
            "INSERT OR REPLACE INTO model_profiles (id, user_id, kind, name, config, is_default, created_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![profile.id, "global", profile.kind, profile.name, config_json, is_default, now],
        )?;
        self.models.add(profile.clone());
        Ok(profile)
    }

    pub fn remove_model(&self, id: &str) -> Result<()> {
        self.db.conn().execute("DELETE FROM model_profiles WHERE id = ?1", params![id])?;
        self.models.remove(id);
        Ok(())
    }

    pub fn set_default_model(&self, id: &str) -> Result<()> {
        if self.models.get(id).is_none() {
            return Err(crate::error::AppError::NotFound(format!("模型不存在: {id}")));
        }
        self.db.conn().execute("UPDATE model_profiles SET is_default = 0", params![])?;
        self.db.conn().execute("UPDATE model_profiles SET is_default = 1 WHERE id = ?1", params![id])?;
        self.models.set_default(Some(id.to_string()));
        Ok(())
    }

    /// Import a local model file (.gguf / .onnx) and register it as a profile.
    pub fn import_model(&self, path: &Path, name: Option<&str>) -> Result<ModelProfile> {
        let path = path
            .canonicalize()
            .map_err(|e| crate::error::AppError::Config(format!("模型文件无效: {e}")))?;
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        let kind = match ext.as_str() {
            "gguf" => "local_gguf",
            "onnx" => "local_onnx",
            _ => return Err(crate::error::AppError::Config("仅支持 .gguf / .onnx 模型文件".into())),
        };
        let default_name = path
            .file_stem()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_default();
        let profile = ModelProfile {
            id: Uuid::new_v4().to_string(),
            name: name.map(|s| s.to_string()).unwrap_or(default_name),
            kind: kind.to_string(),
            config: serde_json::json!({ "model_path": path.to_string_lossy(), "ctx_len": 4096, "model": "local" }),
        };
        self.add_model(profile)
    }

    /// Resolve a provider, auto-starting a local llama.cpp server when the
    /// profile references a `.gguf` model path.
    pub async fn resolve_provider(&self, profile: &ModelProfile) -> Result<Provider> {
        if profile.kind == "local_gguf" {
            if let Some(model_path) = profile.config.get("model_path").and_then(|v| v.as_str()) {
                let ctx_len = profile
                    .config
                    .get("ctx_len")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(4096) as u32;
                let base_url = self.llama.ensure(model_path, ctx_len).await?;
                let model = profile
                    .config
                    .get("model")
                    .and_then(|v| v.as_str())
                    .unwrap_or("local")
                    .to_string();
                return Ok(Arc::new(crate::models::openai_compat::OpenAICompatProvider::new(
                    profile.name.clone(),
                    base_url,
                    model,
                    None,
                )));
            }
        }
        profile.build()
    }

    /// Report bundled runtime availability (for UI diagnostics).
    pub fn runtime_status(&self) -> serde_json::Value {
        serde_json::json!({
            "llama_server": self.llama.is_available(),
            "llama_server_bin": self.llama.server_bin().display().to_string(),
            "python": self.ppt.python_exe.exists(),
            "ppt_master": self.ppt.ppt_master_dir.join("run.py").exists(),
            "tts_engine": self.ppt.tts_engine,
            "libreoffice": self.ppt.libreoffice_exe.as_ref().map(|p| p.exists()).unwrap_or(false),
            "ffmpeg": self.ppt.ffmpeg_exe.as_ref().map(|p| p.exists()).unwrap_or(false)
        })
    }

    // ---- tasks ----
    pub fn create_task(&self, user_id: &str, title: &str, input: &str, model_id: Option<&str>) -> Result<Task> {
        let id = Uuid::new_v4().to_string();
        let now = chrono::Utc::now().timestamp();
        let task = Task {
            id: id.clone(),
            title: title.to_string(),
            input: input.to_string(),
            status: TaskStatus::Pending.as_str().to_string(),
            progress: 0,
            result: None,
        };
        self.db.conn().execute(
            "INSERT INTO tasks (id, user_id, title, input, status, progress, model_id, result, created_at, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9)",
            params![id, user_id, title, input, task.status, task.progress, model_id, None::<String>, now],
        )?;
        Ok(task)
    }

    pub fn list_tasks(&self, user_id: &str) -> Result<Vec<Task>> {
        let conn = self.db.conn();
        let mut stmt = conn.prepare(
            "SELECT id, title, input, status, progress, result FROM tasks WHERE user_id = ?1 ORDER BY created_at DESC",
        )?;
        let rows = stmt.query_map(params![user_id], |r| {
            Ok(Task {
                id: r.get(0)?,
                title: r.get(1)?,
                input: r.get(2)?,
                status: r.get(3)?,
                progress: r.get(4)?,
                result: r.get(5)?,
            })
        })?;
        let mut out = Vec::new();
        for t in rows {
            out.push(t?);
        }
        Ok(out)
    }

    pub fn get_task(&self, id: &str) -> Result<Task> {
        self.db
            .conn()
            .query_row(
                "SELECT id, title, input, status, progress, result FROM tasks WHERE id = ?1",
                params![id],
                |r| {
                    Ok(Task {
                        id: r.get(0)?,
                        title: r.get(1)?,
                        input: r.get(2)?,
                        status: r.get(3)?,
                        progress: r.get(4)?,
                        result: r.get(5)?,
                    })
                },
            )
            .optional()?
            .ok_or_else(|| crate::error::AppError::NotFound(format!("任务不存在: {id}")))
    }

    /// Execute a task using the core agent loop and persist the result.
    pub async fn run_task(&self, id: &str) -> Result<Task> {
        let task = self.get_task(id)?;
        let profile = match self.models.resolve(None) {
            Some(p) => p,
            None => {
                self.set_task_status(id, TaskStatus::Failed, "未配置可用模型".into())?;
                return Err(crate::error::AppError::Model("未配置可用模型".into()));
            }
        };

        let provider = self.resolve_provider(&profile).await?;
        let agent = Agent::new(
            provider,
            self.tools.clone(),
            AgentConfig {
                system_prompt: format!("{}\n\n{}", DEFAULT_SYSTEM_PROMPT, self.plugins.system_context()),
                ..Default::default()
            },
        );
        let ctx = ToolContext {
            workspace_dir: self.config.workspace_dir.clone(),
            allow_commands: true,
            command_whitelist: vec![],
        };

        self.set_task_status(id, TaskStatus::Running, format!("使用模型 {}", profile.name))?;
        match agent.run(&ctx, &task.input).await {
            Ok(answer) => {
                self.set_task_status(id, TaskStatus::Done, answer)?;
            }
            Err(e) => {
                self.set_task_status(id, TaskStatus::Failed, e.to_string())?;
            }
        }
        self.get_task(id)
    }

    fn set_task_status(&self, id: &str, status: TaskStatus, result: String) -> Result<()> {
        let now = chrono::Utc::now().timestamp();
        self.db.conn().execute(
            "UPDATE tasks SET status = ?1, result = ?2, updated_at = ?3 WHERE id = ?4",
            params![status.as_str(), result, now, id],
        )?;
        Ok(())
    }
}

const DEFAULT_SYSTEM_PROMPT: &str = "你是一个离线 AI 智能体。请使用可用工具完成任务，最终用中文给出清晰结论。";

fn load_model_profiles(db: &Db, registry: &ModelRegistry) -> Result<()> {
    let conn = db.conn();
    let mut stmt = conn.prepare("SELECT id, kind, name, config, is_default FROM model_profiles")?;
    let rows = stmt.query_map(params![], |r| {
        Ok((
            r.get::<_, String>(0)?,
            r.get::<_, String>(1)?,
            r.get::<_, String>(2)?,
            r.get::<_, String>(3)?,
            r.get::<_, i64>(4)?,
        ))
    })?;
    let mut default: Option<String> = None;
    for row in rows {
        let (id, kind, name, config, is_default) = row?;
        let config: serde_json::Value = serde_json::from_str(&config).unwrap_or(serde_json::Value::Null);
        let profile = ModelProfile { id: id.clone(), name, kind, config };
        registry.add(profile);
        if is_default == 1 {
            default = Some(id);
        }
    }
    registry.set_default(default);
    Ok(())
}
