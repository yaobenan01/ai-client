// Tauri desktop shell.
//
// 职责：定位并启动 headless core（开发目录或打包后的 sidecar），打开 Web 前端。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tauri::Manager;

fn find_core_binary() -> Option<PathBuf> {
    let exe = if cfg!(windows) { "ai-client.exe" } else { "ai-client" };
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            candidates.push(dir.join(exe));
            // 打包后的 sidecar 形如 ai-client-<target-triple>[.exe]
            if let Ok(entries) = std::fs::read_dir(dir) {
                for e in entries.flatten() {
                    let name = e.file_name().to_string_lossy().to_string();
                    if name == "ai-client" || name == "ai-client.exe" || name.starts_with("ai-client-") {
                        candidates.push(e.path());
                    }
                }
            }
        }
    }
    candidates.push(PathBuf::from("../core/target/debug").join(exe));
    candidates.push(PathBuf::from("../core/target/release").join(exe));

    candidates.into_iter().find(|p| p.exists())
}

fn spawn_core(app: &tauri::App) {
    let data_dir = app.path().app_data_dir().ok().map(|d| d.join("ai-client"));
    let Some(bin) = find_core_binary() else {
        eprintln!("[desktop] 未找到核心引擎二进制 ai-client");
        return;
    };
    let mut cmd = Command::new(&bin);
    if let Some(d) = &data_dir {
        cmd.arg("--data-dir").arg(d);
    }
    cmd.stdout(Stdio::null()).stderr(Stdio::null());
    // TODO(lifecycle): 应用退出时终止 core 进程。
    std::thread::spawn(move || {
        let _ = cmd.spawn();
    });
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            spawn_core(app);
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
