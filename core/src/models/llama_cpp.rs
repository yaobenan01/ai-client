use crate::error::{AppError, Result};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU16, Ordering};
use std::sync::Mutex;
use std::time::Duration;

/// Manages local `llama-server` (llama.cpp) processes.
///
/// A GGUF model is served through llama.cpp's OpenAI-compatible `/v1`
/// endpoint, so the rest of the stack talks to it exactly like any other
/// OpenAI-compatible model — fully offline.
pub struct LlamaServerManager {
    server_bin: PathBuf,
    running: Mutex<HashMap<String, RunningServer>>,
    next_port: AtomicU16,
}

struct RunningServer {
    base_url: String,
    child: tokio::process::Child,
}

impl LlamaServerManager {
    pub fn new(server_bin: PathBuf) -> Self {
        Self {
            server_bin,
            running: Mutex::new(HashMap::new()),
            next_port: AtomicU16::new(18080),
        }
    }

    pub fn server_bin(&self) -> &Path {
        &self.server_bin
    }

    pub fn is_available(&self) -> bool {
        self.server_bin.is_file()
    }

    /// Ensure a llama-server is running for `model_path` and return its base URL.
    pub async fn ensure(&self, model_path: &str, ctx_len: u32) -> Result<String> {
        let key = model_path.to_string();
        if let Some(url) = self.existing_url(&key) {
            return Ok(url);
        }

        let port = self.next_port.fetch_add(1, Ordering::SeqCst);
        let mut child = tokio::process::Command::new(&self.server_bin)
            .arg("-m")
            .arg(model_path)
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg(port.to_string())
            .arg("-c")
            .arg(ctx_len.to_string())
            .arg("--n-gpu-layers")
            .arg("0")
            .kill_on_drop(true)
            .spawn()
            .map_err(|e| AppError::Model(format!("启动 llama-server 失败: {e}")))?;

        let base_url = format!("http://127.0.0.1:{port}/v1");
        wait_ready(&base_url).await?;

        let mut running = self.running.lock().unwrap();
        running.insert(key, RunningServer { base_url: base_url.clone(), child });
        Ok(base_url)
    }

    fn existing_url(&self, key: &str) -> Option<String> {
        let mut running = self.running.lock().unwrap();
        let entry = running.get_mut(key)?;
        // If the child has exited, remove it so we can restart.
        if let Some(status) = entry.child.try_wait().ok().flatten() {
            let _ = status;
            running.remove(key);
            return None;
        }
        Some(entry.base_url.clone())
    }

    /// Stop all managed servers (called on shutdown).
    pub fn stop_all(&self) {
        let mut running = self.running.lock().unwrap();
        for (_, s) in running.drain() {
            let mut child = s.child;
            let _ = child.start_kill();
        }
    }
}

async fn wait_ready(base_url: &str) -> Result<()> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .unwrap_or_else(|_| reqwest::Client::new());
    let health = format!("{}/health", base_url.trim_end_matches("/v1"));
    for _ in 0..120 {
        if let Ok(resp) = client.get(&health).send().await {
            if resp.status().is_success() {
                return Ok(());
            }
        }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    Err(AppError::Model(format!("llama-server 未在预期时间内就绪: {health}")))
}
