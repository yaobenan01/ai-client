use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("database error: {0}")]
    Db(#[from] rusqlite::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("http error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("auth error: {0}")]
    Auth(String),
    #[error("not found: {0}")]
    NotFound(String),
    #[error("invalid config: {0}")]
    Config(String),
    #[error("agent error: {0}")]
    Agent(String),
    #[error("tool error: {0}")]
    Tool(String),
    #[error("plugin error: {0}")]
    Plugin(String),
    #[error("model error: {0}")]
    Model(String),
    #[error("workflow error: {0}")]
    Workflow(String),
    #[error("ppt error: {0}")]
    Ppt(String),
    #[error("unknown error: {0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, AppError>;
