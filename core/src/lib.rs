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

fn detect_llama_server_bin(config: &AppConfig) -> PathBuf {
    let exe = if cfg!(windows) { "llama-server.exe" } else { "llama-server" };

    if let Some(p) = &config.llama_server_bin {
        if p.is_file() {
            return p.clone();
        }
    }
    if let Some(p) = std::env::var_os("AI_CLIENT_LLAMA_SERVER") {
        let pb = PathBuf::from(p);
        if pb.is_file() {
            return pb;
        }
    }
    // 检查当前二进制同级或子目录（安装形态）
    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            let candidates = [
                dir.join(exe),
                dir.join("bin").join(exe),
                dir.join("sidecars").join("llama.cpp").join(exe),
                dir.join("_up_").join("_up_").join("sidecars").join("llama.cpp").join(exe),
            ];
            for c in candidates {
                if c.is_file() {
                    return c;
                }
            }
        }
    }
    // 检查应用数据目录及开发源码目录
    let data_candidates = [
        config.data_dir.join("bin").join(exe),
        config.data_dir.join(exe),
        PathBuf::from("sidecars/llama.cpp").join(exe),
        PathBuf::from("sidecars/llama.cpp/bin").join(exe),
        PathBuf::from("../sidecars/llama.cpp").join(exe),
    ];
    for c in data_candidates {
        if c.is_file() {
            return c;
        }
    }

    PathBuf::from(exe)
}

/// 定位 ppt-master（run.py 所在目录）：显式配置 > 数据目录 > 安装包内置资源 > 源码目录。
fn detect_ppt_master_dir(config: &AppConfig) -> PathBuf {
    let mut candidates: Vec<PathBuf> = Vec::new();

    // 1) 显式环境变量（桌面壳会把安装包内的目录通过它传进来）
    if let Some(p) = std::env::var_os("AI_CLIENT_PPT_MASTER_DIR") {
        candidates.push(PathBuf::from(p));
    }
    // 2) 用户数据目录（升级或手动安装的插件）
    candidates.push(config.plugins_dir.join("ppt-master"));

    // 3) 随安装包分发的内置资源
    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            let mut bases = vec![dir.to_path_buf()];
            if let Some(parent) = dir.parent() {
                bases.push(parent.to_path_buf());
            }
            for base in &bases {
                candidates.push(base.join("plugins").join("ppt-master"));
                candidates.push(base.join("resources").join("plugins").join("ppt-master"));
                candidates.push(
                    base.join("_up_")
                        .join("_up_")
                        .join("plugins")
                        .join("ppt-master"),
                );
                candidates.push(base.join("_up_").join("plugins").join("ppt-master"));
            }
        }
    }

    // 4) 开发源码目录
    candidates.push(PathBuf::from("plugins/ppt-master"));
    candidates.push(PathBuf::from("../plugins/ppt-master"));
    candidates.push(PathBuf::from("../../plugins/ppt-master"));
    candidates.push(PathBuf::from("../../../plugins/ppt-master"));

    for c in &candidates {
        if c.join("run.py").is_file() {
            return c.clone();
        }
    }
    // 找不到时返回数据目录路径，保持既有报错语义
    config.plugins_dir.join("ppt-master")
}

/// 定位 Python 运行时（优先内置自包含运行库，免除用户安装）：显式配置 > 内置 sidecar > 源码目录 > 系统 PATH。
fn detect_python_exe(config: &AppConfig) -> PathBuf {
    if let Some(p) = std::env::var_os("AI_CLIENT_PYTHON") {
        let pb = PathBuf::from(p);
        if pb.is_file() {
            return pb;
        }
    }
    let exe = if cfg!(windows) { "python.exe" } else { "python3" };
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            let mut bases = vec![dir.to_path_buf()];
            if let Some(parent) = dir.parent() {
                bases.push(parent.to_path_buf());
            }
            for base in &bases {
                candidates.push(base.join("_up_").join("_up_").join("sidecars").join("python").join("runtime").join(exe));
                candidates.push(base.join("_up_").join("_up_").join("sidecars").join("python").join("runtime").join("venv").join("Scripts").join(exe));
                candidates.push(base.join("_up_").join("_up_").join("sidecars").join("python").join(exe));
                candidates.push(base.join("resources").join("sidecars").join("python").join("runtime").join(exe));
                candidates.push(base.join("sidecars").join("python").join("runtime").join(exe));
                candidates.push(base.join("python").join("runtime").join(exe));
            }
        }
    }

    candidates.push(PathBuf::from("sidecars/python/runtime").join(exe));
    candidates.push(PathBuf::from("sidecars/python/runtime/venv/Scripts").join(exe));
    candidates.push(PathBuf::from("sidecars/python").join(exe));
    candidates.push(PathBuf::from("../sidecars/python/runtime").join(exe));
    candidates.push(PathBuf::from("../../sidecars/python/runtime").join(exe));
    candidates.push(PathBuf::from("../../../sidecars/python/runtime").join(exe));
    candidates.push(config.data_dir.join("sidecars").join("python").join("runtime").join(exe));

    for c in &candidates {
        if c.is_file() {
            return c.clone();
        }
    }

    if let Ok(path) = std::env::var("PATH") {
        for p in std::env::split_paths(&path) {
            let c = p.join(exe);
            if c.is_file() {
                let s = c.to_string_lossy().to_lowercase();
                if !s.contains("windowsapps") {
                    return c;
                }
            }
        }
    }

    PathBuf::from(exe)
}

/// 定位 LibreOffice 渲染器（内置便携版或系统安装）：显式环境变量 > 内置 sidecar > 常见系统安装路径 > 系统 PATH。
fn detect_libreoffice_exe(_config: &AppConfig) -> Option<PathBuf> {
    if let Some(p) = std::env::var_os("AI_CLIENT_LIBREOFFICE") {
        let pb = PathBuf::from(p);
        if pb.is_file() {
            return Some(pb);
        }
    }
    let exes = if cfg!(windows) {
        vec!["program/soffice.exe", "program/soffice.com", "soffice.exe"]
    } else {
        vec!["soffice", "libreoffice"]
    };
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            let mut bases = vec![dir.to_path_buf()];
            if let Some(parent) = dir.parent() {
                bases.push(parent.to_path_buf());
            }
            for base in &bases {
                for exe in &exes {
                    candidates.push(base.join("_up_").join("_up_").join("sidecars").join("media").join("libreoffice").join(exe));
                    candidates.push(base.join("resources").join("sidecars").join("media").join("libreoffice").join(exe));
                    candidates.push(base.join("sidecars").join("media").join("libreoffice").join(exe));
                }
            }
        }
    }

    for exe in &exes {
        candidates.push(PathBuf::from("sidecars/media/libreoffice").join(exe));
        candidates.push(PathBuf::from("../sidecars/media/libreoffice").join(exe));
        candidates.push(PathBuf::from("../../sidecars/media/libreoffice").join(exe));
        candidates.push(PathBuf::from("../../../sidecars/media/libreoffice").join(exe));
    }

    if cfg!(windows) {
        candidates.push(PathBuf::from("C:\\Program Files\\LibreOffice\\program\\soffice.exe"));
        candidates.push(PathBuf::from("C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe"));
        candidates.push(PathBuf::from("D:\\Program Files\\LibreOffice\\program\\soffice.exe"));
    }

    for c in &candidates {
        if c.is_file() {
            return Some(c.clone());
        }
    }

    if let Ok(path) = std::env::var("PATH") {
        for p in std::env::split_paths(&path) {
            for exe in &["soffice.exe", "soffice.com", "soffice", "libreoffice"] {
                let c = p.join(exe);
                if c.is_file() {
                    return Some(c);
                }
            }
        }
    }

    None
}

/// 定位 FFmpeg 合成器（内置静态构建或系统安装）：显式环境变量 > 内置 sidecar > 系统 PATH。
fn detect_ffmpeg_exe(_config: &AppConfig) -> Option<PathBuf> {
    if let Some(p) = std::env::var_os("AI_CLIENT_FFMPEG") {
        let pb = PathBuf::from(p);
        if pb.is_file() {
            return Some(pb);
        }
    }
    let exes = if cfg!(windows) {
        vec!["bin/ffmpeg.exe", "ffmpeg.exe"]
    } else {
        vec!["bin/ffmpeg", "ffmpeg"]
    };
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            let mut bases = vec![dir.to_path_buf()];
            if let Some(parent) = dir.parent() {
                bases.push(parent.to_path_buf());
            }
            for base in &bases {
                for exe in &exes {
                    candidates.push(base.join("_up_").join("_up_").join("sidecars").join("media").join("ffmpeg").join(exe));
                    candidates.push(base.join("resources").join("sidecars").join("media").join("ffmpeg").join(exe));
                    candidates.push(base.join("sidecars").join("media").join("ffmpeg").join(exe));
                }
            }
        }
    }

    for exe in &exes {
        candidates.push(PathBuf::from("sidecars/media/ffmpeg").join(exe));
        candidates.push(PathBuf::from("../sidecars/media/ffmpeg").join(exe));
        candidates.push(PathBuf::from("../../sidecars/media/ffmpeg").join(exe));
        candidates.push(PathBuf::from("../../../sidecars/media/ffmpeg").join(exe));
    }

    for c in &candidates {
        if c.is_file() {
            return Some(c.clone());
        }
    }

    if let Ok(path) = std::env::var("PATH") {
        let exe = if cfg!(windows) { "ffmpeg.exe" } else { "ffmpeg" };
        for p in std::env::split_paths(&path) {
            let c = p.join(exe);
            if c.is_file() {
                return Some(c);
            }
        }
    }

    None
}

/// 定位 Piper 语音合成器（内置二进制或系统安装）：显式环境变量 > 内置 sidecar > 系统 PATH。
fn detect_piper_exe(_config: &AppConfig) -> Option<PathBuf> {
    if let Some(p) = std::env::var_os("AI_CLIENT_PIPER") {
        let pb = PathBuf::from(p);
        if pb.is_file() {
            return Some(pb);
        }
    }
    let exes = if cfg!(windows) {
        vec!["piper.exe", "piper/piper.exe"]
    } else {
        vec!["piper", "piper/piper"]
    };
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            let mut bases = vec![dir.to_path_buf()];
            if let Some(parent) = dir.parent() {
                bases.push(parent.to_path_buf());
            }
            for base in &bases {
                for exe in &exes {
                    candidates.push(base.join("_up_").join("_up_").join("sidecars").join("tts").join("piper").join(exe));
                    candidates.push(base.join("resources").join("sidecars").join("tts").join("piper").join(exe));
                    candidates.push(base.join("sidecars").join("tts").join("piper").join(exe));
                }
            }
        }
    }

    for exe in &exes {
        candidates.push(PathBuf::from("sidecars/tts/piper").join(exe));
        candidates.push(PathBuf::from("../sidecars/tts/piper").join(exe));
        candidates.push(PathBuf::from("../../sidecars/tts/piper").join(exe));
        candidates.push(PathBuf::from("../../../sidecars/tts/piper").join(exe));
    }

    for c in &candidates {
        if c.is_file() {
            return Some(c.clone());
        }
    }

    if let Ok(path) = std::env::var("PATH") {
        let exe = if cfg!(windows) { "piper.exe" } else { "piper" };
        for p in std::env::split_paths(&path) {
            let c = p.join(exe);
            if c.is_file() {
                return Some(c);
            }
        }
    }

    None
}

/// 定位 Piper 中文语音模型权重：显式环境变量 > 内置 sidecar。
fn detect_piper_model(_config: &AppConfig) -> Option<PathBuf> {
    if let Some(p) = std::env::var_os("PIPER_MODEL") {
        let pb = PathBuf::from(p);
        if pb.is_file() {
            return Some(pb);
        }
    }
    let model_name = "zh_CN-huayan-medium.onnx";
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            let mut bases = vec![dir.to_path_buf()];
            if let Some(parent) = dir.parent() {
                bases.push(parent.to_path_buf());
            }
            for base in &bases {
                candidates.push(base.join("_up_").join("_up_").join("sidecars").join("tts").join("models").join(model_name));
                candidates.push(base.join("resources").join("sidecars").join("tts").join("models").join(model_name));
                candidates.push(base.join("sidecars").join("tts").join("models").join(model_name));
            }
        }
    }

    candidates.push(PathBuf::from("sidecars/tts/models").join(model_name));
    candidates.push(PathBuf::from("../sidecars/tts/models").join(model_name));
    candidates.push(PathBuf::from("../../sidecars/tts/models").join(model_name));
    candidates.push(PathBuf::from("../../../sidecars/tts/models").join(model_name));

    for c in &candidates {
        if c.is_file() {
            return Some(c.clone());
        }
    }

    None
}

impl Core {
    /// Initialize the core: open DB, apply schema, load persisted state.
    pub fn init(config: AppConfig) -> Result<Self> {
        let db = Db::open(&config.db_path())?;
        let auth = AuthService::new(db.clone());
        let models = Arc::new(ModelRegistry::new());
        load_model_profiles(&db, &models)?;

        let ppt = PptRuntime::detect(PptRuntimeConfig {
            python_exe: Some(detect_python_exe(&config)),
            ppt_master_dir: Some(detect_ppt_master_dir(&config)),
            libreoffice_exe: detect_libreoffice_exe(&config),
            ffmpeg_exe: detect_ffmpeg_exe(&config),
            piper_exe: detect_piper_exe(&config),
            piper_model: detect_piper_model(&config),
            tts_engine: "piper".into(),
        })?;
        let ppt_arc = Arc::new(ppt.clone());
        let tools = Arc::new(crate::tools::default_registry_with_ppt(ppt_arc));
        let plugins = PluginManager::new(config.plugins_dir.clone());

        let llama_bin = detect_llama_server_bin(&config);
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
        let python_ready = self.ppt.python_exe.is_file()
            || (!self.ppt.python_exe.to_string_lossy().is_empty()
                && self.ppt.python_exe != std::path::Path::new("python")
                && self.ppt.python_exe != std::path::Path::new("python3")
                && self.ppt.python_exe.exists());
        serde_json::json!({
            "llama_server": self.llama.is_available(),
            "llama_server_bin": self.llama.server_bin().display().to_string(),
            "python": python_ready,
            "ppt_master": self.ppt.ppt_master_dir.join("run.py").exists(),
            "tts_engine": self.ppt.tts_engine,
            "libreoffice": self.ppt.libreoffice_exe.as_ref().map(|p| p.is_file()).unwrap_or(false),
            "ffmpeg": self.ppt.ffmpeg_exe.as_ref().map(|p| p.is_file()).unwrap_or(false),
            "piper": self.ppt.piper_exe.as_ref().map(|p| p.is_file()).unwrap_or(false),
            "piper_model": self.ppt.piper_model.as_ref().map(|p| p.is_file()).unwrap_or(false)
        })
    }

    // ---- model diagnostic ----
    pub async fn test_model(&self, id: &str, prompt: Option<&str>) -> Result<serde_json::Value> {
        let profile = self
            .models
            .resolve(Some(id))
            .ok_or_else(|| crate::error::AppError::NotFound(format!("模型不存在: {id}")))?;
        let provider = self.resolve_provider(&profile).await?;
        let start = std::time::Instant::now();
        let prompt_text = prompt.unwrap_or("你好！请简短回答并确认连通成功。");
        let resp = provider
            .chat(
                &[crate::models::ChatMessage {
                    role: "user".into(),
                    content: prompt_text.to_string(),
                    ..Default::default()
                }],
                &[],
                128,
            )
            .await?;
        let latency_ms = start.elapsed().as_millis();
        Ok(serde_json::json!({
            "ok": true,
            "id": profile.id,
            "name": profile.name,
            "kind": profile.kind,
            "latency_ms": latency_ms,
            "response": resp.content,
            "finish_reason": resp.finish_reason
        }))
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
            logs: Some("[]".into()),
            artifacts: Some("[]".into()),
            model_id: model_id.map(|s| s.to_string()),
            created_at: Some(now),
            updated_at: Some(now),
        };
        self.db.conn().execute(
            "INSERT INTO tasks (id, user_id, title, input, status, progress, model_id, result, logs, artifacts, created_at, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?11)",
            params![
                id,
                user_id,
                title,
                input,
                task.status,
                task.progress,
                model_id,
                None::<String>,
                task.logs,
                task.artifacts,
                now
            ],
        )?;
        Ok(task)
    }

    pub fn list_tasks(&self, user_id: &str) -> Result<Vec<Task>> {
        let conn = self.db.conn();
        let mut stmt = conn.prepare(
            "SELECT id, title, input, status, progress, result, logs, artifacts, model_id, created_at, updated_at
             FROM tasks WHERE user_id = ?1 ORDER BY created_at DESC",
        )?;
        let rows = stmt.query_map(params![user_id], |r| {
            Ok(Task {
                id: r.get(0)?,
                title: r.get(1)?,
                input: r.get(2)?,
                status: r.get(3)?,
                progress: r.get(4)?,
                result: r.get(5)?,
                logs: r.get(6)?,
                artifacts: r.get(7)?,
                model_id: r.get(8)?,
                created_at: r.get(9)?,
                updated_at: r.get(10)?,
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
                "SELECT id, title, input, status, progress, result, logs, artifacts, model_id, created_at, updated_at
                 FROM tasks WHERE id = ?1",
                params![id],
                |r| {
                    Ok(Task {
                        id: r.get(0)?,
                        title: r.get(1)?,
                        input: r.get(2)?,
                        status: r.get(3)?,
                        progress: r.get(4)?,
                        result: r.get(5)?,
                        logs: r.get(6)?,
                        artifacts: r.get(7)?,
                        model_id: r.get(8)?,
                        created_at: r.get(9)?,
                        updated_at: r.get(10)?,
                    })
                },
            )
            .optional()?
            .ok_or_else(|| crate::error::AppError::NotFound(format!("任务不存在: {id}")))
    }

    pub fn cancel_task(&self, id: &str) -> Result<()> {
        let now = chrono::Utc::now().timestamp();
        self.db.conn().execute(
            "UPDATE tasks SET status = 'cancelled', result = '任务已由用户手动停止', updated_at = ?1 WHERE id = ?2",
            params![now, id],
        )?;
        Ok(())
    }

    pub fn delete_task(&self, id: &str) -> Result<()> {
        self.db.conn().execute("DELETE FROM tasks WHERE id = ?1", params![id])?;
        Ok(())
    }

    /// Execute a task using the core agent loop with step observability and artifact tracking.
    pub async fn run_task(&self, id: &str) -> Result<Task> {
        let task = self.get_task(id)?;
        let model_id_ref = task.model_id.as_deref();
        let profile = match self.models.resolve(model_id_ref) {
            Some(p) => p,
            None => {
                self.update_task_record(id, TaskStatus::Failed, 0, "未配置可用模型", "[]", "[]")?;
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

        let before_files = collect_workspace_artifacts(&self.config.workspace_dir);

        let initial_steps = vec![crate::agent::TaskStep {
            step: 0,
            action: "thought".into(),
            tool_name: None,
            input: None,
            output: Some(format!("启动任务，使用模型: {}", profile.name)),
            timestamp: chrono::Utc::now().timestamp(),
        }];
        let logs_str = serde_json::to_string(&initial_steps).unwrap_or_else(|_| "[]".into());
        self.update_task_record(id, TaskStatus::Running, 10, &format!("使用模型 {}", profile.name), &logs_str, "[]")?;

        let db = self.db.clone();
        let task_id = id.to_string();
        let collected_steps = Arc::new(std::sync::Mutex::new(initial_steps));
        let steps_clone = collected_steps.clone();

        let run_res = agent
            .run_with_reporter(&ctx, &task.input, move |step_num, step| {
                let mut guard = steps_clone.lock().unwrap();
                guard.push(step.clone());
                let progress = (10 + (step_num * 80 / 24).min(80)) as i64;
                let logs_json = serde_json::to_string(&*guard).unwrap_or_default();
                let now = chrono::Utc::now().timestamp();
                let _ = db.conn().execute(
                    "UPDATE tasks SET progress = ?1, logs = ?2, updated_at = ?3 WHERE id = ?4",
                    params![progress, logs_json, now, task_id],
                );
            })
            .await;

        let after_files = collect_workspace_artifacts(&self.config.workspace_dir);
        let new_artifacts: Vec<String> = after_files
            .into_iter()
            .filter(|f| !before_files.contains(f))
            .collect();
        let artifacts_json = serde_json::to_string(&new_artifacts).unwrap_or_else(|_| "[]".into());

        let final_steps = collected_steps.lock().unwrap().clone();
        let final_logs = serde_json::to_string(&final_steps).unwrap_or_else(|_| "[]".into());

        match run_res {
            Ok(output) => {
                self.update_task_record(
                    id,
                    TaskStatus::Done,
                    100,
                    &output.final_answer,
                    &final_logs,
                    &artifacts_json,
                )?;
            }
            Err(e) => {
                self.update_task_record(
                    id,
                    TaskStatus::Failed,
                    100,
                    &e.to_string(),
                    &final_logs,
                    &artifacts_json,
                )?;
            }
        }
        self.get_task(id)
    }

    fn update_task_record(
        &self,
        id: &str,
        status: TaskStatus,
        progress: i64,
        result: &str,
        logs: &str,
        artifacts: &str,
    ) -> Result<()> {
        let now = chrono::Utc::now().timestamp();
        self.db.conn().execute(
            "UPDATE tasks SET status = ?1, progress = ?2, result = ?3, logs = ?4, artifacts = ?5, updated_at = ?6 WHERE id = ?7",
            params![status.as_str(), progress, result, logs, artifacts, now, id],
        )?;
        Ok(())
    }

    // ---- direct quick actions & workspace file manager ----
    pub fn quick_generate_pptx(&self, input_path: Option<&str>, content: Option<&str>) -> Result<PathBuf> {
        let exports_dir = self.config.workspace_dir.join("exports");
        std::fs::create_dir_all(&exports_dir)?;
        let input_file = if let Some(path) = input_path.filter(|s| !s.trim().is_empty()) {
            let p = PathBuf::from(path);
            if p.is_absolute() { p } else { self.config.workspace_dir.join(p) }
        } else if let Some(text) = content.filter(|s| !s.trim().is_empty()) {
            let temp_name = format!("content_{}.md", chrono::Utc::now().timestamp());
            let temp_file = exports_dir.join(temp_name);
            std::fs::write(&temp_file, text)?;
            temp_file
        } else {
            return Err(crate::error::AppError::Config("必须提供材料路径或 Markdown 文本".into()));
        };
        self.ppt.generate_pptx(&input_file, &exports_dir)
    }

    pub fn quick_pptx_to_video(&self, pptx_path: &str, output_path: Option<&str>) -> Result<PathBuf> {
        let exports_dir = self.config.workspace_dir.join("exports");
        std::fs::create_dir_all(&exports_dir)?;
        let p = PathBuf::from(pptx_path);
        let src = if p.is_absolute() { p } else { self.config.workspace_dir.join(p) };
        let out = if let Some(o) = output_path.filter(|s| !s.trim().is_empty()) {
            let op = PathBuf::from(o);
            if op.is_absolute() { op } else { self.config.workspace_dir.join(op) }
        } else {
            let stem = src.file_stem().and_then(|s| s.to_str()).unwrap_or("presentation");
            exports_dir.join(format!("{}_{}.mp4", stem, chrono::Utc::now().timestamp()))
        };
        self.ppt.pptx_to_video(&src, &out)
    }

    pub fn list_workspace_files(&self) -> Result<Vec<serde_json::Value>> {
        let mut files = Vec::new();
        let base = &self.config.workspace_dir;
        let mut dirs = vec![base.clone()];
        let exports = base.join("exports");
        if exports.exists() {
            dirs.push(exports);
        }
        for dir in dirs {
            if let Ok(entries) = std::fs::read_dir(&dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_file() {
                        let rel = path
                            .strip_prefix(base)
                            .unwrap_or(&path)
                            .to_string_lossy()
                            .replace('\\', "/");
                        let ext = path
                            .extension()
                            .and_then(|s| s.to_str())
                            .unwrap_or("")
                            .to_lowercase();
                        let size = entry.metadata().map(|m| m.len()).unwrap_or(0);
                        let modified = entry
                            .metadata()
                            .and_then(|m| m.modified())
                            .ok()
                            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                            .map(|d| d.as_secs())
                            .unwrap_or(0);
                        files.push(serde_json::json!({
                            "name": path.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default(),
                            "path": rel,
                            "ext": ext,
                            "size": size,
                            "modified": modified
                        }));
                    }
                }
            }
        }
        files.sort_by(|a, b| b["modified"].as_u64().cmp(&a["modified"].as_u64()));
        Ok(files)
    }

    /// 解析工作区内的相对路径，拒绝越界访问。
    pub fn resolve_workspace_path(&self, rel: &str) -> Result<PathBuf> {
        let clean = rel.trim_start_matches(|c| c == '/' || c == '\\').replace("..", "");
        if clean.trim().is_empty() {
            return Err(crate::error::AppError::Config("缺少文件路径".into()));
        }
        let full = self.config.workspace_dir.join(&clean);
        if !full.is_file() {
            return Err(crate::error::AppError::NotFound(format!("文件不存在: {clean}")));
        }
        Ok(full)
    }

    /// 用系统默认程序打开工作区内的文件。
    pub fn open_workspace_file(&self, rel: &str) -> Result<()> {
        let path = self.resolve_workspace_path(rel)?;
        open_with_system(&path)
    }

    /// 在系统文件管理器中定位（选中）工作区内的文件。
    pub fn reveal_workspace_file(&self, rel: &str) -> Result<()> {
        let path = self.resolve_workspace_path(rel)?;
        reveal_with_system(&path)
    }
}

/// 启动一个完全脱离的子进程（不等待其结束）。
fn spawn_detached(program: &str, args: &[std::ffi::OsString]) -> Result<()> {
    std::process::Command::new(program)
        .args(args)
        .spawn()
        .map_err(|e| crate::error::AppError::Other(format!("启动 {program} 失败: {e}")))?;
    Ok(())
}

/// 用系统默认程序打开文件。
fn open_with_system(path: &Path) -> Result<()> {
    let arg = path.as_os_str().to_os_string();
    if cfg!(target_os = "windows") {
        // start 的第一个参数是窗口标题，必须显式给空串，
        // 否则含空格的路径会被当成标题、文件打不开。
        spawn_detached(
            "cmd",
            &[
                std::ffi::OsString::from("/C"),
                std::ffi::OsString::from("start"),
                std::ffi::OsString::from(""),
                arg,
            ],
        )
    } else if cfg!(target_os = "macos") {
        spawn_detached("open", &[arg])
    } else {
        spawn_detached("xdg-open", &[arg])
    }
}

/// 在系统文件管理器中定位文件。
fn reveal_with_system(path: &Path) -> Result<()> {
    if cfg!(target_os = "windows") {
        // explorer 要求 /select, 与路径同参数、不能有空格
        let mut select = std::ffi::OsString::from("/select,");
        select.push(path.as_os_str());
        spawn_detached("explorer", &[select])
    } else if cfg!(target_os = "macos") {
        spawn_detached(
            "open",
            &[std::ffi::OsString::from("-R"), path.as_os_str().to_os_string()],
        )
    } else {
        let dir = path.parent().unwrap_or(path);
        spawn_detached("xdg-open", &[dir.as_os_str().to_os_string()])
    }
}

fn collect_workspace_artifacts(workspace: &Path) -> std::collections::HashSet<String> {
    let mut set = std::collections::HashSet::new();
    let exports = workspace.join("exports");
    let dirs = vec![workspace.to_path_buf(), exports];
    for dir in dirs {
        if let Ok(entries) = std::fs::read_dir(&dir) {
            for e in entries.flatten() {
                let p = e.path();
                if p.is_file() {
                    let ext = p.extension().and_then(|s| s.to_str()).unwrap_or("").to_lowercase();
                    if matches!(ext.as_str(), "pptx" | "mp4" | "pdf" | "png") {
                        if let Ok(rel) = p.strip_prefix(workspace) {
                            set.insert(rel.to_string_lossy().replace('\\', "/"));
                        }
                    }
                }
            }
        }
    }
    set
}

const DEFAULT_SYSTEM_PROMPT: &str = r#"你是一个强大、专业的离线 AI 智能体工作站。你的职责是充分调用本地可用工具与插件，高效完成用户的任务。

【执行与规划准则】
1. 步骤清晰透明：当执行多步骤任务（尤其是制作演示文稿、口播视频、文档整理等）时，请务必在思维分析或回复中明确说明当前所处阶段：
   - [阶段 1/4] 分析需求、提炼大纲与页面架构设计
   - [阶段 2/4] 调用 generate_pptx 生成 16:9 原生多版式 PPTX
   - [阶段 3/4] 调用 pptx_to_video 渲染高清幻灯片并合成配音
   - [阶段 4/4] 汇总交付物并输出结论说明
2. 工具调用规范：
   - 生成 PPT 时优先调用 generate_pptx，支持直接传入 content (Markdown 大纲) 或 input_path (现有文件)。
   - 生成口播视频时调用 pptx_to_video，传入生成的 pptx_path。
3. 最终交付结论（finish）：
   - 请以结构化 Markdown 输出，包含：
     - 🎯 任务达成概况
     - 📑 演示文稿及视频规格（页数、视觉主题、口播时长等）
     - 📦 交付物清单（列出具体路径）
     - 💡 后续使用与编辑建议"#;

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


