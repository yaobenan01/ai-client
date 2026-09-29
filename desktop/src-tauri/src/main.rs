// Tauri desktop shell.
//
// 职责：定位并启动 headless core（开发目录或打包后的 sidecar），打开 Web 前端。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
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

fn spawn_core(app: &tauri::App, child_slot: Arc<Mutex<Option<Child>>>) {
    let data_dir = app.path().app_data_dir().ok().map(|d| d.join("ai-client"));
    let Some(bin) = find_core_binary() else {
        eprintln!("[desktop] 未找到核心引擎二进制 ai-client");
        return;
    };
    let mut cmd = Command::new(&bin);
    cmd.arg("serve");
    if let Some(d) = &data_dir {
        let _ = std::fs::create_dir_all(d);
        cmd.arg("--data-dir").arg(d);

        // 将 core 输出写入日志文件便于排查
        if let Ok(log_file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(d.join("core.log"))
        {
            if let Ok(err_file) = log_file.try_clone() {
                cmd.stdout(Stdio::from(log_file));
                cmd.stderr(Stdio::from(err_file));
            }
        }
    }

    match cmd.spawn() {
        Ok(child) => {
            if let Ok(mut slot) = child_slot.lock() {
                *slot = Some(child);
            }
        }
        Err(e) => {
            eprintln!("[desktop] 启动 core 失败: {e}");
        }
    }
}

fn main() {
    let child_holder: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
    let child_for_setup = child_holder.clone();
    let child_for_exit = child_holder.clone();

    tauri::Builder::default()
        .setup(move |app| {
            spawn_core(app, child_for_setup);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(move |_app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                if let Ok(mut lock) = child_for_exit.lock() {
                    if let Some(mut child) = lock.take() {
                        let _ = child.kill();
                    }
                }
            }
        });
}
