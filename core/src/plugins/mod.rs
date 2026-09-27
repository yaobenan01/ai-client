use crate::error::{AppError, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

/// Metadata for an installed skill/plugin, parsed from its SKILL.md.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillInfo {
    pub id: String,
    pub name: String,
    pub description: String,
    pub path: PathBuf,
    pub enabled: bool,
}

/// Scans a plugins directory for `SKILL.md`-style skills.
#[derive(Debug, Clone)]
pub struct PluginManager {
    pub plugins_dir: PathBuf,
}

impl PluginManager {
    pub fn new(plugins_dir: PathBuf) -> Self {
        std::fs::create_dir_all(&plugins_dir).ok();
        Self { plugins_dir }
    }

    pub fn list(&self) -> Vec<SkillInfo> {
        let mut skills = Vec::new();
        let Ok(entries) = std::fs::read_dir(&self.plugins_dir) else {
            return skills;
        };
        for entry in entries.flatten() {
            if !entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                continue;
            }
            let dir = entry.path();
            let skill_md = dir.join("SKILL.md");
            if !skill_md.exists() {
                continue;
            }
            let raw = std::fs::read_to_string(&skill_md).unwrap_or_default();
            let (name, description) = parse_skill_md(&raw);
            skills.push(SkillInfo {
                id: dir.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default(),
                name: if name.is_empty() { dir.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default() } else { name },
                description,
                path: dir,
                enabled: true,
            });
        }
        skills.sort_by(|a, b| a.name.cmp(&b.name));
        skills
    }

    /// Copy a skill directory into the plugins dir (offline install).
    pub fn install(&self, source: &Path) -> Result<SkillInfo> {
        if !source.join("SKILL.md").exists() {
            return Err(AppError::Plugin("目录中缺少 SKILL.md".into()));
        }
        let id = source.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default();
        let dest = self.plugins_dir.join(&id);
        copy_dir_recursive(source, &dest)?;
        let skills = self.list();
        skills
            .into_iter()
            .find(|s| s.id == id)
            .ok_or_else(|| AppError::Plugin("安装后未找到插件".into()))
    }

    /// Append enabled skill descriptions to the agent system prompt.
    pub fn system_context(&self) -> String {
        let mut out = String::new();
        for s in self.list() {
            if s.enabled && !s.description.is_empty() {
                out.push_str(&format!("[技能 {}] {}\n", s.name, s.description));
            }
        }
        out
    }
}

/// Parse a SKILL.md: prefer YAML `name:`/`description:` frontmatter, then
/// fall back to the first markdown heading.
fn parse_skill_md(raw: &str) -> (String, String) {
    let mut name = String::new();
    let mut desc = String::new();
    let mut in_frontmatter = false;

    for line in raw.lines() {
        let t = line.trim();
        if t == "---" {
            in_frontmatter = !in_frontmatter;
            continue;
        }
        if in_frontmatter {
            if let Some(v) = t.strip_prefix("name:") {
                name = v.trim().trim_matches('"').to_string();
            } else if let Some(v) = t.strip_prefix("description:") {
                desc = v.trim().trim_matches('"').to_string();
                if desc == ">" || desc == "|" {
                    desc = String::new();
                }
            } else if !desc.is_empty() && (t.starts_with("> ") || t.starts_with('-') || t.starts_with("  ")) {
                // continue folding description
                desc.push(' ');
                desc.push_str(t.trim().trim_start_matches("> "));
            }
            continue;
        }
        if name.is_empty() && t.starts_with("# ") {
            name = t.trim_start_matches("# ").to_string();
        }
    }

    // Fallback: first non-empty line as name when missing.
    if name.is_empty() {
        for line in raw.lines() {
            let t = line.trim();
            if !t.is_empty() && !t.starts_with('#') && !t.starts_with('-') {
                name = t.chars().take(60).collect();
                break;
            }
        }
    }
    (name.trim().to_string(), desc.trim().to_string())
}

fn copy_dir_recursive(src: &Path, dst: &Path) -> Result<()> {
    std::fs::create_dir_all(dst)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let ty = entry.file_type()?;
        let from = entry.path();
        let to = dst.join(entry.file_name());
        if ty.is_dir() {
            copy_dir_recursive(&from, &to)?;
        } else {
            std::fs::copy(&from, &to)?;
        }
    }
    Ok(())
}
