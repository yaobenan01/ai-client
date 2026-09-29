// Tauri desktop shell.
//
// 职责：定位并启动 headless core（开发目录或打包后的 sidecar），打开 Web 前端。
//
// 可用性约定（务必保持）：
// 1. Windows 下绝不弹出控制台窗口（CREATE_NO_WINDOW），否则黑色终端会挡住界面。
// 2. 若 8787 上已有 core 在运行（上次残留/手动启动），直接复用，不重复拉起导致端口冲突。
// 3. 把安装包内置的 ppt-master / llama-server 通过环境变量交给 core，做到开箱即用。
// 4. core 的 stdout/stderr 写入 <data_dir>/core.log；写不了就丢弃，绝不继承控制台。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::Manager;

const CORE_HOST: &str = "127.0.0.1";
const CORE_PORT: u16 = 8787;

/// Windows 下隐藏 console 窗口，避免弹出黑色终端挡住界面。
#[cfg(windows)]
fn apply_no_window(cmd: &mut Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
    cmd.creation_flags(CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP);
}

#[cfg(not(windows))]
fn apply_no_window(_cmd: &mut Command) {}

fn port_listening(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok()
}

/// 收集可能的资源基目录：安装资源目录、可执行文件目录及其若干层祖先、工作目录。
fn push_unique(list: &mut Vec<PathBuf>, p: PathBuf) {
    if !list.contains(&p) {
        list.push(p);
    }
}

fn resource_bases(app: &tauri::App) -> Vec<PathBuf> {
    let mut bases: Vec<PathBuf> = Vec::new();

    if let Ok(dir) = app.path().resource_dir() {
        push_unique(&mut bases, dir);
    }
    if let Ok(exe) = std::env::current_exe() {
        let mut cur = exe.parent().map(|p| p.to_path_buf());
        let mut steps = 0;
        while let Some(d) = cur {
            if steps >= 5 {
                break;
            }
            push_unique(&mut bases, d.clone());
            cur = d.parent().map(|p| p.to_path_buf());
            steps += 1;
        }
    }
    if let Ok(cwd) = std::env::current_dir() {
        push_unique(&mut bases, cwd);
    }
    bases
}

/// 在基目录下尝试若干固定布局，返回第一个存在的候选。
fn first_existing(candidates: impl IntoIterator<Item = PathBuf>) -> Option<PathBuf> {
    candidates.into_iter().find(|p| p.exists())
}

/// 兜底：在 root 下做有预算的浅层扫描（避免在大目录上卡启动）。
fn scan_for(root: &Path, name: &str, depth: usize, budget: &mut usize) -> Option<PathBuf> {
    if depth == 0 || *budget == 0 {
        return None;
    }
    let mut subdirs: Vec<PathBuf> = Vec::new();
    for entry in std::fs::read_dir(root).ok()?.flatten() {
        if *budget == 0 {
            break;
        }
        *budget -= 1;
        let path = entry.path();
        if path.file_name().and_then(|n| n.to_str()) == Some(name) {
            return Some(path);
        }
        if path.is_dir() {
            subdirs.push(path);
        }
    }
    for dir in subdirs {
        if let Some(found) = scan_for(&dir, name, depth - 1, budget) {
            return Some(found);
        }
    }
    None
}

/// 定位内置的 ppt-master（run.py 所在目录）。
fn discover_ppt_master(app: &tauri::App) -> Option<PathBuf> {
    let bases = resource_bases(app);
    let mut candidates: Vec<PathBuf> = Vec::new();
    for base in &bases {
        candidates.push(base.join("plugins").join("ppt-master"));
        candidates.push(base.join("_up_").join("plugins").join("ppt-master"));
        candidates.push(base.join("_up_").join("_up_").join("plugins").join("ppt-master"));
        candidates.push(base.join("resources").join("plugins").join("ppt-master"));
        candidates.push(
            base.join("resources")
                .join("_up_")
                .join("_up_")
                .join("plugins")
                .join("ppt-master"),
        );
    }
    if let Some(dir) = first_existing(candidates) {
        if dir.join("run.py").is_file() {
            return Some(dir);
        }
    }
    // 兜底扫描：只在安装资源目录/可执行文件目录做有限深度搜索。
    let mut budget = 1200usize;
    for base in bases.iter().take(2) {
        if let Some(dir) = scan_for(base, "ppt-master", 4, &mut budget) {
            if dir.join("run.py").is_file() {
                return Some(dir);
            }
        }
    }
    None
}

/// 定位内置的 llama-server。
fn discover_llama_server(app: &tauri::App) -> Option<PathBuf> {
    let exe = if cfg!(windows) { "llama-server.exe" } else { "llama-server" };
    let bases = resource_bases(app);
    let mut candidates: Vec<PathBuf> = Vec::new();
    for base in &bases {
        for prefix in [
            PathBuf::new(),
            PathBuf::from("_up_"),
            PathBuf::from("_up_").join("_up_"),
            PathBuf::from("resources"),
        ] {
            candidates.push(base.join(&prefix).join("sidecars").join("llama.cpp").join(exe));
            candidates.push(base.join(&prefix).join("bin").join(exe));
            candidates.push(base.join(&prefix).join(exe));
        }
    }
    if let Some(bin) = first_existing(candidates) {
        return Some(bin);
    }
    let mut budget = 1200usize;
    for base in bases.iter().take(2) {
        if let Some(bin) = scan_for(base, exe, 4, &mut budget) {
            return Some(bin);
        }
    }
    None
}

/// 定位随包分发的 Python 运行时（免用户自行安装 Python 的关键）。
fn discover_python(app: &tauri::App) -> Option<PathBuf> {
    let bases = resource_bases(app);
    let names: &[&str] = if cfg!(windows) {
        &["python.exe"]
    } else {
        &["bin/python3", "python3", "bin/python"]
    };
    let mut candidates: Vec<PathBuf> = Vec::new();
    for base in &bases {
        for name in names {
            let rel = PathBuf::from(name);
            for prefix in [
                PathBuf::new(),
                PathBuf::from("_up_").join("_up_"),
                PathBuf::from("resources"),
            ] {
                candidates.push(base.join(&prefix).join("python").join("runtime").join(&rel));
                candidates.push(base.join(&prefix).join("python").join(&rel));
                candidates.push(
                    base.join(&prefix)
                        .join("sidecars")
                        .join("python")
                        .join("runtime")
                        .join(&rel),
                );
            }
        }
    }
    first_existing(candidates)
}
/// 定位 core 可执行文件；务必排除桌面壳自身，避免自启动递归。
fn find_core_binary() -> Option<PathBuf> {
    let exe = if cfg!(windows) { "ai-client.exe" } else { "ai-client" };
    let self_exe = std::env::current_exe().ok().and_then(|p| p.canonicalize().ok());

    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(cur) = std::env::current_exe() {
        if let Some(dir) = cur.parent() {
            candidates.push(dir.join(exe));
            // 打包后的 sidecar 形如 ai-client-<target-triple>[.exe]
            if let Ok(entries) = std::fs::read_dir(dir) {
                for e in entries.flatten() {
                    let name = e.file_name().to_string_lossy().to_string();
                    if name.starts_with("ai-client-") && !name.contains("desktop") {
                        candidates.push(e.path());
                    }
                }
            }
        }
    }
    candidates.push(PathBuf::from("../core/target/debug").join(exe));
    candidates.push(PathBuf::from("../core/target/release").join(exe));

    for c in candidates {
        if !c.is_file() {
            continue;
        }
        // 绝不允许把桌面壳当成 core 拉起来（否则会无限自启动）。
        if let (Ok(canon), Some(self_canon)) = (c.canonicalize(), self_exe.as_ref()) {
            if &canon == self_canon {
                continue;
            }
        }
        return Some(c);
    }
    None
}

fn spawn_core(app: &tauri::App, child_slot: Arc<Mutex<Option<Child>>>) {
    // 已有 core 在跑（上次未退出的残留进程），直接复用，避免端口冲突后整个平台不可用。
    if port_listening(CORE_PORT) {
        return;
    }

    let Some(bin) = find_core_binary() else {
        eprintln!("[desktop] 未找到核心引擎二进制 ai-client");
        return;
    };

    let data_dir = app.path().app_data_dir().ok().map(|d| d.join("ai-client"));
    if let Some(d) = &data_dir {
        let _ = std::fs::create_dir_all(d);
    }

    let mut cmd = Command::new(&bin);
    cmd.arg("serve")
        .arg("--host")
        .arg(CORE_HOST)
        .arg("--port")
        .arg(CORE_PORT.to_string());
    if let Some(d) = &data_dir {
        cmd.arg("--data-dir").arg(d);
    }

    // 把安装包内置的资源交给 core（免安装 Python/llama.cpp 的关键）。
    if let Some(dir) = discover_ppt_master(app) {
        cmd.env("AI_CLIENT_PPT_MASTER_DIR", &dir);
    }
    if let Some(bin) = discover_llama_server(app) {
        cmd.env("AI_CLIENT_LLAMA_SERVER", &bin);
    }
    if let Some(py) = discover_python(app) {
        cmd.env("AI_CLIENT_PYTHON", &py);
    }

    let mut logged = false;
    if let Some(d) = &data_dir {
        if let Ok(file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(d.join("core.log"))
        {
            if let Ok(err_file) = file.try_clone() {
                cmd.stdout(Stdio::from(file));
                cmd.stderr(Stdio::from(err_file));
                logged = true;
            }
        }
    }
    if !logged {
        // 即使拿不到日志句柄，也不能继承控制台，否则又会弹出黑窗。
        cmd.stdout(Stdio::null());
        cmd.stderr(Stdio::null());
    }
    cmd.stdin(Stdio::null());

    apply_no_window(&mut cmd);

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

/// 升级后清理 WebView2 的 Service Worker / HTTP 缓存。
///
/// 背景：旧版本在桌面端注册过 Service Worker，它会缓存上一版 index.html；升级后
/// 该 HTML 引用的 hash 资源已不存在，窗口就会一直空白。这里按版本号做一次性清理，
/// 保证即使旧 SW 的自毁逻辑没来得及生效，用户也能直接恢复可用。
fn clear_webview_caches_once() {
    let Some(local) = std::env::var_os("LOCALAPPDATA") else {
        return;
    };
    // 与 tauri.conf.json 的 identifier 保持一致
    let base = PathBuf::from(local).join("com.local.aiclient");
    let marker = base.join(format!(".cache-cleared-{}", env!("CARGO_PKG_VERSION")));
    if marker.exists() {
        return;
    }
    let webview = base.join("EBWebView").join("Default");
    if webview.is_dir() {
        for sub in ["Service Worker", "Cache", "Code Cache"] {
            let target = webview.join(sub);
            // 安全校验：只允许删除 WebView2 配置目录内部的子目录
            if target.starts_with(&webview) && target.is_dir() {
                let _ = std::fs::remove_dir_all(&target);
            }
        }
    }
    let _ = std::fs::write(&marker, b"ok");
}

fn main() {
    // 必须在 Tauri/WebView2 初始化之前执行，否则缓存目录被占用。
    clear_webview_caches_once();

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
            if matches!(event, tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. }) {
                if let Ok(mut lock) = child_for_exit.lock() {
                    if let Some(mut child) = lock.take() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        });
}


