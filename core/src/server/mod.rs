use crate::error::AppError;
use crate::Core;
use axum::{
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    routing::{delete, get, post},
    Json, Router,
};
use serde_json::{json, Value};
use std::sync::Arc;
use tower_http::cors::CorsLayer;

/// Build the headless HTTP API router (docker-headless style).
pub fn router(core: Arc<Core>) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/api/auth/register", post(register))
        .route("/api/auth/login", post(login))
        .route("/api/auth/logout", post(logout))
        .route("/api/auth/me", get(me))
        .route("/api/models", get(list_models).post(add_model))
        .route("/api/models/import", post(import_model))
        .route("/api/models/:id/default", post(set_default_model))
        .route("/api/models/:id/test", post(test_model))
        .route("/api/models/:id", delete(remove_model))
        .route("/api/tasks", get(list_tasks).post(create_task))
        .route("/api/tasks/:id", get(get_task).delete(delete_task))
        .route("/api/tasks/:id/run", post(run_task))
        .route("/api/tasks/:id/cancel", post(cancel_task))
        .route("/api/ppt/quick-generate", post(quick_generate_pptx))
        .route("/api/ppt/quick-video", post(quick_pptx_to_video))
        .route("/api/workspace/files", get(list_workspace_files))
        .route("/api/workspace/download/*path", get(download_workspace_file))
        .route("/api/workspace/open", post(open_workspace_artifact))
        .route("/api/workspace/reveal", post(reveal_workspace_artifact))
        .route("/api/plugins", get(list_plugins))
        .route("/api/plugins/install", post(install_plugin))
        .route("/api/system/info", get(system_info))
        .route("/api/system/runtimes", get(runtime_status))
        .layer(CorsLayer::permissive())
        .with_state(core)
}

type AppState = State<Arc<Core>>;
type ApiResult = std::result::Result<Json<Value>, ApiError>;

struct ApiError(StatusCode, Value);

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(self.1)).into_response()
    }
}

impl From<AppError> for ApiError {
    fn from(e: AppError) -> Self {
        let status = match &e {
            AppError::NotFound(_) => StatusCode::NOT_FOUND,
            AppError::Auth(_) => StatusCode::UNAUTHORIZED,
            _ => StatusCode::BAD_REQUEST,
        };
        ApiError(status, json!({ "error": e.to_string() }))
    }
}

fn bearer(headers: &HeaderMap) -> Option<String> {
    headers
        .get("authorization")?
        .to_str()
        .ok()?
        .strip_prefix("Bearer ")
        .map(|s| s.to_string())
}

fn current_user(core: &Core, headers: &HeaderMap) -> std::result::Result<crate::auth::User, ApiError> {
    let token = bearer(headers).ok_or_else(|| ApiError(StatusCode::UNAUTHORIZED, json!({"error":"缺少认证信息"})))?;
    core.verify_session(&token).map_err(ApiError::from)
}

async fn health() -> Json<Value> {
    Json(json!({ "status": "ok", "name": "ai-client-core" }))
}

async fn register(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let username = body["username"].as_str().unwrap_or_default();
    let password = body["password"].as_str().unwrap_or_default();
    let user = core.register(username, password)?;
    Ok(Json(json!({ "user": user })))
}

async fn login(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let username = body["username"].as_str().unwrap_or_default();
    let password = body["password"].as_str().unwrap_or_default();
    let session = core.login(username, password)?;
    Ok(Json(json!({ "token": session.token, "user": session.user })))
}

async fn logout(State(core): AppState, headers: HeaderMap) -> ApiResult {
    let user = current_user(&core, &headers)?;
    let token = bearer(&headers).unwrap_or_default();
    core.logout(&token)?;
    let _ = user;
    Ok(Json(json!({ "ok": true })))
}

async fn me(State(core): AppState, headers: HeaderMap) -> ApiResult {
    let user = current_user(&core, &headers)?;
    Ok(Json(json!({ "user": user })))
}

async fn list_models(State(core): AppState) -> ApiResult {
    Ok(Json(json!({ "models": core.list_models(), "default": core.models.default_id() })))
}

async fn add_model(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let profile = crate::models::ModelProfile {
        id: body["id"].as_str().unwrap_or_default().to_string(),
        name: body["name"].as_str().unwrap_or("未命名模型").to_string(),
        kind: body["kind"].as_str().unwrap_or("local_gguf").to_string(),
        config: body.get("config").cloned().unwrap_or(Value::Null),
    };
    let profile = core.add_model(profile)?;
    Ok(Json(json!({ "model": profile })))
}

async fn import_model(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let path = body["path"].as_str().unwrap_or_default();
    let name = body["name"].as_str();
    let profile = core.import_model(std::path::Path::new(path), name)?;
    Ok(Json(json!({ "model": profile })))
}

async fn set_default_model(State(core): AppState, Path(id): Path<String>) -> ApiResult {
    core.set_default_model(&id)?;
    Ok(Json(json!({ "ok": true, "default": id })))
}

async fn remove_model(State(core): AppState, Path(id): Path<String>) -> ApiResult {
    core.remove_model(&id)?;
    Ok(Json(json!({ "ok": true })))
}

async fn list_tasks(State(core): AppState, headers: HeaderMap) -> ApiResult {
    let user = current_user(&core, &headers)?;
    Ok(Json(json!({ "tasks": core.list_tasks(&user.id)? })))
}

async fn create_task(State(core): AppState, headers: HeaderMap, Json(body): Json<Value>) -> ApiResult {
    let user = current_user(&core, &headers)?;
    let title = body["title"].as_str().unwrap_or("新任务").to_string();
    let input = body["input"].as_str().unwrap_or_default().to_string();
    let model_id = body["model_id"].as_str().map(|s| s.to_string());
    let task = core.create_task(&user.id, &title, &input, model_id.as_deref())?;
    Ok(Json(json!({ "task": task })))
}

async fn get_task(State(core): AppState, Path(id): Path<String>) -> ApiResult {
    Ok(Json(json!({ "task": core.get_task(&id)? })))
}

async fn run_task(State(core): AppState, Path(id): Path<String>) -> ApiResult {
    let handle = core.clone();
    let task_id = id.clone();
    tokio::spawn(async move {
        let _ = handle.run_task(&task_id).await;
    });
    Ok(Json(json!({ "task": core.get_task(&id)?, "started": true })))
}

async fn test_model(State(core): AppState, Path(id): Path<String>, Json(body): Json<Value>) -> ApiResult {
    let prompt = body["prompt"].as_str();
    let res = core.test_model(&id, prompt).await?;
    Ok(Json(res))
}

async fn list_plugins(State(core): AppState) -> ApiResult {
    Ok(Json(json!({ "plugins": core.plugins.list() })))
}

async fn install_plugin(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let path = body["path"].as_str().unwrap_or_default();
    let skill = core.plugins.install(std::path::Path::new(path))?;
    Ok(Json(json!({ "plugin": skill })))
}

async fn cancel_task(State(core): AppState, Path(id): Path<String>) -> ApiResult {
    core.cancel_task(&id)?;
    Ok(Json(json!({ "ok": true, "cancelled": id })))
}

async fn delete_task(State(core): AppState, Path(id): Path<String>) -> ApiResult {
    core.delete_task(&id)?;
    Ok(Json(json!({ "ok": true, "deleted": id })))
}

async fn quick_generate_pptx(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let input_path = body["input_path"].as_str();
    let content = body["content"].as_str();
    let pptx_path = core.quick_generate_pptx(input_path, content)?;
    let rel = pptx_path
        .strip_prefix(&core.config.workspace_dir)
        .unwrap_or(&pptx_path)
        .to_string_lossy()
        .replace('\\', "/");
    Ok(Json(json!({
        "ok": true,
        "path": rel,
        "filename": pptx_path.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default()
    })))
}

async fn quick_pptx_to_video(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let pptx_path = body["pptx_path"].as_str().unwrap_or_default();
    let output_path = body["output_path"].as_str();
    let video_path = core.quick_pptx_to_video(pptx_path, output_path)?;
    let rel = video_path
        .strip_prefix(&core.config.workspace_dir)
        .unwrap_or(&video_path)
        .to_string_lossy()
        .replace('\\', "/");
    Ok(Json(json!({
        "ok": true,
        "path": rel,
        "filename": video_path.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default()
    })))
}

async fn list_workspace_files(State(core): AppState) -> ApiResult {
    let files = core.list_workspace_files()?;
    Ok(Json(json!({ "files": files })))
}

async fn download_workspace_file(
    State(core): AppState,
    Path(rel_path): Path<String>,
) -> std::result::Result<Response, ApiError> {
    let clean = rel_path.trim_start_matches('/').replace("..", "");
    let full = core.config.workspace_dir.join(&clean);
    if !full.exists() || !full.is_file() {
        return Err(ApiError(StatusCode::NOT_FOUND, json!({"error": "文件不存在"})));
    }
    let filename = full.file_name().and_then(|s| s.to_str()).unwrap_or("file");
    let ext = full.extension().and_then(|s| s.to_str()).unwrap_or("").to_lowercase();
    let content_type = match ext.as_str() {
        "pptx" => "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "mp4" => "video/mp4",
        "pdf" => "application/pdf",
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "json" => "application/json",
        "md" | "txt" => "text/plain; charset=utf-8",
        _ => "application/octet-stream",
    };
    let bytes = std::fs::read(&full)
        .map_err(|e| ApiError(StatusCode::INTERNAL_SERVER_ERROR, json!({"error": e.to_string()})))?;

    let disposition = format!("inline; filename=\"{filename}\"");
    Ok((
        [
            (axum::http::header::CONTENT_TYPE, content_type),
            (axum::http::header::CONTENT_DISPOSITION, &disposition),
        ],
        bytes,
    )
        .into_response())
}

/// 用系统默认程序打开工作区内的产物（桌面端主要交互入口）。
async fn open_workspace_artifact(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let path = body["path"].as_str().unwrap_or_default();
    core.open_workspace_file(path)?;
    Ok(Json(json!({ "ok": true, "path": path })))
}

/// 在系统文件管理器中定位并选中工作区内的产物。
async fn reveal_workspace_artifact(State(core): AppState, Json(body): Json<Value>) -> ApiResult {
    let path = body["path"].as_str().unwrap_or_default();
    core.reveal_workspace_file(path)?;
    Ok(Json(json!({ "ok": true, "path": path })))
}

async fn system_info(State(core): AppState) -> ApiResult {
    Ok(Json(json!({
        "version": env!("CARGO_PKG_VERSION"),
        "data_dir": core.config.data_dir,
        "models_dir": core.config.models_dir,
        "workspace_dir": core.config.workspace_dir,
    })))
}

async fn runtime_status(State(core): AppState) -> ApiResult {
    Ok(Json(json!({ "runtimes": core.runtime_status() })))
}
