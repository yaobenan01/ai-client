use crate::error::{AppError, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::process::Command;

/// Configuration for the bundled PPT/视频 runtime ("ppt-master" integration).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PptRuntimeConfig {
    /// Override the Python interpreter; falls back to env / `python3`.
    pub python_exe: Option<PathBuf>,
    /// Directory containing the ppt-master skill (with run.py / render_video.py).
    pub ppt_master_dir: Option<PathBuf>,
    pub libreoffice_exe: Option<PathBuf>,
    pub ffmpeg_exe: Option<PathBuf>,
    pub piper_exe: Option<PathBuf>,
    pub piper_model: Option<PathBuf>,
    /// `piper` (lightweight local), `cosyvoice`, or `auto`.
    pub tts_engine: String,
}

impl Default for PptRuntimeConfig {
    fn default() -> Self {
        Self {
            python_exe: None,
            ppt_master_dir: None,
            libreoffice_exe: None,
            ffmpeg_exe: None,
            piper_exe: None,
            piper_model: None,
            tts_engine: "piper".into(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct PptRuntime {
    pub python_exe: PathBuf,
    pub ppt_master_dir: PathBuf,
    pub libreoffice_exe: Option<PathBuf>,
    pub ffmpeg_exe: Option<PathBuf>,
    pub piper_exe: Option<PathBuf>,
    pub piper_model: Option<PathBuf>,
    pub tts_engine: String,
}

impl PptRuntime {
    pub fn detect(cfg: PptRuntimeConfig) -> Result<Self> {
        let python_exe = cfg
            .python_exe
            .or_else(|| std::env::var_os("AI_CLIENT_PYTHON").map(PathBuf::from))
            .unwrap_or_else(|| PathBuf::from(if cfg!(windows) { "python" } else { "python3" }));

        let ppt_master_dir = cfg
            .ppt_master_dir
            .or_else(|| std::env::var_os("AI_CLIENT_PPT_MASTER_DIR").map(PathBuf::from))
            .ok_or_else(|| AppError::Ppt("未配置 ppt-master 目录".into()))?;

        // 允许通过环境变量注入随包分发的渲染/合成工具，免去用户自行安装。
        let libreoffice_exe = cfg
            .libreoffice_exe
            .or_else(|| std::env::var_os("AI_CLIENT_LIBREOFFICE").map(PathBuf::from));
        let ffmpeg_exe = cfg
            .ffmpeg_exe
            .or_else(|| std::env::var_os("AI_CLIENT_FFMPEG").map(PathBuf::from));
        let piper_exe = cfg
            .piper_exe
            .or_else(|| std::env::var_os("AI_CLIENT_PIPER").map(PathBuf::from));
        let piper_model = cfg
            .piper_model
            .or_else(|| std::env::var_os("PIPER_MODEL").map(PathBuf::from));

        Ok(Self {
            python_exe,
            ppt_master_dir,
            libreoffice_exe,
            ffmpeg_exe,
            piper_exe,
            piper_model,
            tts_engine: cfg.tts_engine,
        })
    }

    /// Generate an editable PPTX from a source document (PDF/DOCX/Markdown/text).
    pub fn generate_pptx(&self, input: &Path, output_dir: &Path) -> Result<PathBuf> {
        let script = self.ppt_master_dir.join("run.py");
        if !script.exists() {
            return Err(AppError::Ppt(format!("缺少脚本 {}", script.display())));
        }
        std::fs::create_dir_all(output_dir)?;
        let status = Command::new(&self.python_exe)
            .arg(&script)
            .arg("generate")
            .arg("--input")
            .arg(input)
            .arg("--out")
            .arg(output_dir)
            .status()
            .map_err(|e| AppError::Ppt(format!("无法启动 Python: {e}")))?;
        if !status.success() {
            return Err(AppError::Ppt(format!("PPT 生成失败，退出码 {:?}", status.code())));
        }
        // run.py writes `<name>_<timestamp>.pptx`; locate the newest file.
        newest_pptx(output_dir)
    }

    /// Render a PPTX into a narrated MP4 (offline TTS + FFmpeg).
    pub fn pptx_to_video(&self, pptx: &Path, output: &Path) -> Result<PathBuf> {
        let script = self.ppt_master_dir.join("render_video.py");
        if !script.exists() {
            return Err(AppError::Ppt(format!("缺少脚本 {}", script.display())));
        }
        if let Some(parent) = output.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let mut cmd = Command::new(&self.python_exe);
        cmd.arg(&script)
            .arg("--pptx")
            .arg(pptx)
            .arg("--out")
            .arg(output)
            .arg("--tts")
            .arg(&self.tts_engine);
        // 仅在内置/显式配置时覆盖，避免把脚本已有的环境探测清空。
        if let Some(p) = &self.ffmpeg_exe {
            cmd.env("AI_CLIENT_FFMPEG", p);
        }
        if let Some(p) = &self.libreoffice_exe {
            cmd.env("AI_CLIENT_LIBREOFFICE", p);
        }
        if let Some(p) = &self.piper_exe {
            cmd.env("AI_CLIENT_PIPER", p);
        }
        if let Some(p) = &self.piper_model {
            cmd.env("PIPER_MODEL", p);
        }
        let status = cmd
            .status()
            .map_err(|e| AppError::Ppt(format!("无法启动视频渲染: {e}")))?;
        if !status.success() {
            return Err(AppError::Ppt(format!("视频渲染失败，退出码 {:?}", status.code())));
        }
        Ok(output.to_path_buf())
    }
}

fn newest_pptx(dir: &Path) -> Result<PathBuf> {
    let mut found: Vec<_> = std::fs::read_dir(dir)?
        .flatten()
        .filter(|e| e.path().extension().map(|x| x.eq_ignore_ascii_case("pptx")).unwrap_or(false))
        .collect();
    found.sort_by_key(|e| e.metadata().and_then(|m| m.modified()).unwrap_or(std::time::SystemTime::UNIX_EPOCH));
    found
        .last()
        .map(|e| e.path())
        .ok_or_else(|| AppError::Ppt("未找到生成的 .pptx 文件".into()))
}
