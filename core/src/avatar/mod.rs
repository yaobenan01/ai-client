use crate::error::{AppError, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AvatarPreset {
    pub id: String,
    pub name: String,
    pub gender: String,
    pub title: String,
    pub avatar_badge: String,
    pub default_voice: String,
    pub default_voice_fallback: Option<String>,
    pub description: String,
    pub preview_color: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AvatarRenderRequest {
    #[serde(default = "default_mode")]
    pub mode: String, // "standalone" | "ppt_pip"
    pub avatar_id: String,
    pub text: String,
    pub audio_path: Option<String>,
    pub voice: Option<String>,
    pub rate: Option<String>,
    pub pitch: Option<String>,
    pub tts_engine: Option<String>,
    pub background: Option<String>,
    pub chroma_key: Option<bool>,
    pub no_subtitles: Option<bool>,
    pub pptx_path: Option<String>,
    pub ppt_video_path: Option<String>,
    pub pip_pos: Option<String>,
    pub pip_style: Option<String>,
    pub pip_scale: Option<f32>,
    pub output_path: Option<String>,
    pub custom_avatar_path: Option<String>,
}

fn default_mode() -> String {
    "standalone".into()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AvatarRenderResponse {
    pub success: bool,
    pub output_path: String,
    pub mode: String,
    pub avatar_id: String,
    pub srt_path: Option<String>,
    pub master_audio: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AvatarRuntimeConfig {
    pub python_exe: Option<PathBuf>,
    pub avatar_master_dir: Option<PathBuf>,
    pub presets_dir: Option<PathBuf>,
    pub models_dir: Option<PathBuf>,
    pub ffmpeg_exe: Option<PathBuf>,
    pub piper_exe: Option<PathBuf>,
    pub piper_model: Option<PathBuf>,
}

#[derive(Debug, Clone)]
pub struct AvatarRuntime {
    pub python_exe: PathBuf,
    pub avatar_master_dir: PathBuf,
    pub presets_dir: PathBuf,
    pub models_dir: PathBuf,
    pub ffmpeg_exe: Option<PathBuf>,
    pub piper_exe: Option<PathBuf>,
    pub piper_model: Option<PathBuf>,
}

impl AvatarRuntime {
    pub fn detect(cfg: AvatarRuntimeConfig) -> Result<Self> {
        let python_exe = cfg
            .python_exe
            .or_else(|| std::env::var_os("AI_CLIENT_PYTHON").map(PathBuf::from))
            .unwrap_or_else(|| PathBuf::from(if cfg!(windows) { "python" } else { "python3" }));

        let avatar_master_dir = cfg
            .avatar_master_dir
            .or_else(|| std::env::var_os("AI_CLIENT_AVATAR_MASTER_DIR").map(PathBuf::from))
            .ok_or_else(|| AppError::Internal("未配置 avatar-master 目录".into()))?;

        let presets_dir = cfg
            .presets_dir
            .or_else(|| std::env::var_os("AI_CLIENT_AVATAR_PRESETS_DIR").map(PathBuf::from))
            .unwrap_or_else(|| avatar_master_dir.join("../../sidecars/avatar/presets"));

        let models_dir = cfg
            .models_dir
            .or_else(|| std::env::var_os("AI_CLIENT_AVATAR_MODELS_DIR").map(PathBuf::from))
            .unwrap_or_else(|| avatar_master_dir.join("../../sidecars/avatar/models"));

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
            avatar_master_dir,
            presets_dir,
            models_dir,
            ffmpeg_exe,
            piper_exe,
            piper_model,
        })
    }

    /// List registered digital human anchor presets.
    pub fn list_presets(&self) -> Vec<AvatarPreset> {
        let presets_json = self.presets_dir.join("presets.json");
        if presets_json.is_file() {
            if let Ok(content) = std::fs::read_to_string(&presets_json) {
                if let Ok(list) = serde_json::from_str::<Vec<AvatarPreset>>(&content) {
                    return list;
                }
            }
        }

        // Built-in presets fallback
        vec![
            AvatarPreset {
                id: "boyang".into(),
                name: "伯洋".into(),
                gender: "male".into(),
                title: "资深金融 / 政务男主播".into(),
                avatar_badge: "权威沉稳".into(),
                default_voice: "zh-CN-YunxiNeural".into(),
                default_voice_fallback: Some("zh_CN-huayan-medium".into()),
                description: "声音稳健庄重、咬字清晰，适合政策解读、新闻宣讲与正式工作汇报。".into(),
                preview_color: "#1e293b".into(),
                tags: vec!["政务播报".into(), "年终述职".into(), "金融财讯".into(), "高管演讲".into()],
            },
            AvatarPreset {
                id: "wanqing".into(),
                name: "婉清".into(),
                gender: "female".into(),
                title: "优雅知性 / 科技早报女主播".into(),
                avatar_badge: "温和典雅".into(),
                default_voice: "zh-CN-XiaoxiaoNeural".into(),
                default_voice_fallback: Some("zh_CN-huayan-medium".into()),
                description: "声线温润柔和、节奏自然，适合公司简介、科技早报与高端产品推介。".into(),
                preview_color: "#2d3748".into(),
                tags: vec!["科技前沿".into(), "品牌宣传".into(), "早间播报".into(), "企业文化".into()],
            },
            AvatarPreset {
                id: "zhiming".into(),
                name: "志明".into(),
                gender: "male".into(),
                title: "亲和商务 / 课件培训导师".into(),
                avatar_badge: "亲和教学".into(),
                default_voice: "zh-CN-YunjianNeural".into(),
                default_voice_fallback: Some("zh_CN-huayan-medium".into()),
                description: "表达生动流畅、亲和力强，适合在线微课、产品操作指南与员工入职培训。".into(),
                preview_color: "#1e3a5f".into(),
                tags: vec!["培训课件".into(), "操作指引".into(), "公开讲座".into(), "知识科普".into()],
            },
            AvatarPreset {
                id: "xinyue".into(),
                name: "馨月".into(),
                gender: "female".into(),
                title: "青春活力 / 新潮体验推介官".into(),
                avatar_badge: "元气活力".into(),
                default_voice: "zh-CN-XiaoyiNeural".into(),
                default_voice_fallback: Some("zh_CN-huayan-medium".into()),
                description: "声音灵动清脆、极具感染力，适合文旅宣传、活动发布与电商带货讲解。".into(),
                preview_color: "#3b1e3a".into(),
                tags: vec!["文旅推广".into(), "新潮探店".into(), "快闪发布".into(), "活动邀约".into()],
            },
        ]
    }

    /// Render a digital human video according to the specified request.
    pub fn render(&self, req: AvatarRenderRequest) -> Result<AvatarRenderResponse> {
        let script = self.avatar_master_dir.join("run_avatar.py");
        if !script.exists() {
            return Err(AppError::Internal(format!("缺少数字人主脚本 {}", script.display())));
        }

        let mut cmd = Command::new(&self.python_exe);
        cmd.arg(&script);
        cmd.arg("--mode").arg(&req.mode);
        cmd.arg("--avatar-id").arg(&req.avatar_id);
        cmd.arg("--text").arg(&req.text);

        if let Some(audio) = &req.audio_path {
            cmd.arg("--audio").arg(audio);
        }
        if let Some(voice) = &req.voice {
            cmd.arg("--voice").arg(voice);
        }
        if let Some(rate) = &req.rate {
            cmd.arg(format!("--rate={rate}"));
        }
        if let Some(pitch) = &req.pitch {
            cmd.arg(format!("--pitch={pitch}"));
        }
        if let Some(tts_engine) = &req.tts_engine {
            cmd.arg("--tts-engine").arg(tts_engine);
        }
        if let Some(bg) = &req.background {
            cmd.arg("--background").arg(bg);
        }
        if req.chroma_key.unwrap_or(false) {
            cmd.arg("--chroma-key");
        }
        if req.no_subtitles.unwrap_or(false) {
            cmd.arg("--no-subtitles");
        }
        if let Some(pptx) = &req.pptx_path {
            cmd.arg("--pptx").arg(pptx);
        }
        if let Some(ppt_vid) = &req.ppt_video_path {
            cmd.arg("--ppt-video").arg(ppt_vid);
        }
        if let Some(pos) = &req.pip_pos {
            cmd.arg("--pip-pos").arg(pos);
        }
        if let Some(style) = &req.pip_style {
            cmd.arg("--pip-style").arg(style);
        }
        if let Some(scale) = req.pip_scale {
            cmd.arg("--pip-scale").arg(scale.to_string());
        }
        if let Some(out) = &req.output_path {
            cmd.arg("--out").arg(out);
        }
        if let Some(custom) = &req.custom_avatar_path {
            cmd.arg("--custom-avatar-media").arg(custom);
        }

        cmd.arg("--presets-dir").arg(&self.presets_dir);
        let model_path = self.models_dir.join("wav2lip.onnx");
        if model_path.is_file() {
            cmd.arg("--model-path").arg(&model_path);
        }

        // Environment overrides
        if let Some(p) = &self.ffmpeg_exe {
            cmd.env("AI_CLIENT_FFMPEG_PATH", p);
            cmd.env("AI_CLIENT_FFMPEG", p);
        }
        if let Some(p) = &self.piper_exe {
            cmd.env("AI_CLIENT_PIPER_PATH", p);
            cmd.env("AI_CLIENT_PIPER", p);
        }
        if let Some(p) = &self.piper_model {
            cmd.env("AI_CLIENT_PIPER_MODEL", p);
            cmd.env("PIPER_MODEL", p);
        }

        let output = cmd
            .output()
            .map_err(|e| AppError::Internal(format!("无法启动数字人合成进程: {e}")))?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        if !output.status.success() {
            let last_err = stderr.lines().rev().take(10).collect::<Vec<_>>().into_iter().rev().collect::<Vec<_>>().join("\n");
            return Err(AppError::Internal(format!(
                "数字人合成失败 (退出码 {:?}): {}",
                output.status.code(),
                if last_err.is_empty() { stdout.lines().rev().take(5).collect::<Vec<_>>().join("\n") } else { last_err }
            )));
        }

        // Extract JSON marker from stdout
        if let Some(start_idx) = stdout.find("__RESULT_JSON__") {
            let json_sub = &stdout[start_idx + "__RESULT_JSON__".len()..];
            if let Some(end_idx) = json_sub.find("__END_RESULT__") {
                let json_str = &json_sub[..end_idx];
                if let Ok(res) = serde_json::from_str::<AvatarRenderResponse>(json_str) {
                    return Ok(res);
                }
            }
        }

        // Fallback: If output_path was provided or can be found
        if let Some(out) = req.output_path {
            return Ok(AvatarRenderResponse {
                success: true,
                output_path: out,
                mode: req.mode,
                avatar_id: req.avatar_id,
                srt_path: None,
                master_audio: None,
            });
        }

        Err(AppError::Internal("数字人合成完成但未能解析产物信息".into()))
    }
}
