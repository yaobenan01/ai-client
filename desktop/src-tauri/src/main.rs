// Tauri desktop shell.
//
// The shell's only job is to launch the headless core (bundled or from the
// dev target) and open the web frontend, which talks to the core over
// localhost HTTP. This keeps the desktop app and the PWA on the same
// architecture.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::{Command, Stdio};
use tauri::Manager;

fn spawn_core(app: &tauri::App) {
    let data_dir = app.path().app_data_dir().ok().map(|d| d.join("ai-client"));
    let exe = if cfg!(windows) { "ai-client.exe" } else { "ai-client" };

    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            candidates.push(dir.join(exe));
        }
    }
    candidates.push(PathBuf::from("../core/target/debug").join(exe));
    candidates.push(PathBuf::from("../core/target/release").join(exe));

    if let Some(bin) = candidates.into_iter().find(|p| p.exists()) {
        let mut cmd = Command::new(&bin);
        if let Some(d) = &data_dir {
            cmd.arg("--data-dir").arg(d);
        }
        cmd.stdout(Stdio::null()).stderr(Stdio::null());
        // TODO(lifecycle): terminate the core when the app exits.
        std::thread::spawn(move || {
            let _ = cmd.spawn();
        });
    }
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
