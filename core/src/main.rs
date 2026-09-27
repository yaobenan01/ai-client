use ai_client_core::config::AppConfig;
use ai_client_core::server;
use ai_client_core::Core;
use clap::{Args, Parser, Subcommand};
use std::path::PathBuf;
use std::sync::Arc;

#[derive(Parser)]
#[command(name = "ai-client", version, about = "离线 AI 智能体核心引擎（headless）")]
struct Cli {
    #[command(subcommand)]
    command: Option<Cmd>,
}

#[derive(Subcommand)]
enum Cmd {
    /// 启动本地 HTTP 服务（默认）
    Serve(ServeArgs),
}

#[derive(Args)]
struct ServeArgs {
    /// 数据目录（数据库/模型/插件/工作区）
    #[arg(long)]
    data_dir: Option<PathBuf>,
    /// 监听地址
    #[arg(long, default_value = "127.0.0.1")]
    host: String,
    /// 监听端口
    #[arg(long, default_value_t = 8787)]
    port: u16,
}

fn default_data_dir() -> PathBuf {
    if let Some(d) = std::env::var_os("AI_CLIENT_DATA_DIR") {
        return PathBuf::from(d);
    }
    let base = if cfg!(windows) {
        std::env::var_os("APPDATA")
    } else {
        std::env::var_os("HOME")
    };
    match base {
        Some(b) => PathBuf::from(b).join("ai-client"),
        None => PathBuf::from(".ai-client-data"),
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,ai_client_core=debug".into()),
        )
        .init();

    let cli = Cli::parse();
    let args = match cli.command {
        Some(Cmd::Serve(a)) => a,
        None => ServeArgs { data_dir: None, host: "127.0.0.1".into(), port: 8787 },
    };

    let data_dir = args.data_dir.unwrap_or_else(default_data_dir);
    let mut config = AppConfig::at(data_dir)?;
    config.server.host = args.host;
    config.server.port = args.port;

    let core = Arc::new(Core::init(config)?);
    let app = server::router(core.clone());
    let addr = format!("{}:{}", core.config.server.host, core.config.server.port);
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    tracing::info!("ai-client-core listening on http://{addr}");
    axum::serve(listener, app).await?;
    Ok(())
}
