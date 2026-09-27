use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Root directory for all app data (defaults to platform data dir).
    pub data_dir: PathBuf,
    /// Directory containing user-imported model files (.gguf / .onnx).
    pub models_dir: PathBuf,
    /// Directory containing installed plugins/skills.
    pub plugins_dir: PathBuf,
    /// Directory where task artifacts (.pptx / .mp4 ...) are written.
    pub workspace_dir: PathBuf,
    /// Headless HTTP server configuration.
    pub server: ServerConfig,
    /// Default model profile id to use when a task does not specify one.
    pub default_model: Option<String>,
    /// Path to the bundled llama.cpp `llama-server` binary (optional).
    pub llama_server_bin: Option<PathBuf>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self { host: "127.0.0.1".into(), port: 8787 }
    }
}

impl AppConfig {
    /// Build a config rooted at `data_dir`, creating sub-directories on disk.
    pub fn at(data_dir: PathBuf) -> std::io::Result<Self> {
        let models_dir = data_dir.join("models");
        let plugins_dir = data_dir.join("plugins");
        let workspace_dir = data_dir.join("workspace");
        for d in [&data_dir, &models_dir, &plugins_dir, &workspace_dir] {
            std::fs::create_dir_all(d)?;
        }
        Ok(Self {
            data_dir,
            models_dir,
            plugins_dir,
            workspace_dir,
            server: ServerConfig::default(),
            default_model: None,
            llama_server_bin: None,
        })
    }

    pub fn db_path(&self) -> PathBuf {
        self.data_dir.join("app.sqlite3")
    }
}
