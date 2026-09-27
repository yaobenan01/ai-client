use crate::error::{AppError, Result};
use crate::storage::Db;
use argon2::{
    password_hash::{PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};
use rand_core::OsRng;
use chrono::Utc;
use rusqlite::{params, OptionalExtension};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

pub const SESSION_TTL_SECS: i64 = 60 * 60 * 24 * 30; // 30 days

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: String,
    pub username: String,
    pub role: String,
    pub created_at: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub token: String,
    pub user: User,
}

#[derive(Clone)]
pub struct AuthService {
    db: Db,
}

impl AuthService {
    pub fn new(db: Db) -> Self {
        Self { db }
    }

    pub fn register(&self, username: &str, password: &str) -> Result<User> {
        let username = username.trim();
        if username.is_empty() || password.len() < 6 {
            return Err(AppError::Auth("用户名不能为空且密码至少 6 位".into()));
        }
        let id = Uuid::new_v4().to_string();
        let hash = hash_password(password)?;
        let now = Utc::now().timestamp();
        let inserted = self.db.conn().execute(
            "INSERT INTO users (id, username, pass_hash, role, created_at) VALUES (?1, ?2, ?3, 'user', ?4)",
            params![id, username, hash, now],
        );
        match inserted {
            Ok(_) => Ok(User { id, username: username.to_string(), role: "user".into(), created_at: now }),
            Err(rusqlite::Error::SqliteFailure(e, _)) if e.code == rusqlite::ErrorCode::ConstraintViolation => {
                Err(AppError::Auth("用户名已存在".into()))
            }
            Err(e) => Err(e.into()),
        }
    }

    pub fn login(&self, username: &str, password: &str) -> Result<Session> {
        let user = self.find_by_username(username)?;
        let row = self
            .db
            .conn()
            .query_row(
                "SELECT id, username, pass_hash, role, created_at FROM users WHERE id = ?1",
                params![user.id],
                |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, String>(1)?,
                        r.get::<_, String>(2)?,
                        r.get::<_, String>(3)?,
                        r.get::<_, i64>(4)?,
                    ))
                },
            )
            .optional()?
            .ok_or_else(|| AppError::Auth("用户不存在".into()))?;
        let (id, username, pass_hash, role, created_at) = row;
        if !verify_password(password, &pass_hash) {
            return Err(AppError::Auth("密码错误".into()));
        }
        self.issue_session(User { id, username, role, created_at })
    }

    pub fn verify_session(&self, token: &str) -> Result<User> {
        let now = Utc::now().timestamp();
        let user = self
            .db
            .conn()
            .query_row(
                "SELECT u.id, u.username, u.role, u.created_at
                 FROM sessions s JOIN users u ON u.id = s.user_id
                 WHERE s.token = ?1 AND s.expires_at > ?2",
                params![token, now],
                |r| {
                    Ok(User {
                        id: r.get(0)?,
                        username: r.get(1)?,
                        role: r.get(2)?,
                        created_at: r.get(3)?,
                    })
                },
            )
            .optional()?
            .ok_or_else(|| AppError::Auth("会话无效或已过期".into()))?;
        Ok(user)
    }

    pub fn logout(&self, token: &str) -> Result<()> {
        self.db.conn().execute("DELETE FROM sessions WHERE token = ?1", params![token])?;
        Ok(())
    }

    fn find_by_username(&self, username: &str) -> Result<User> {
        self.db
            .conn()
            .query_row(
                "SELECT id, username, role, created_at FROM users WHERE username = ?1",
                params![username],
                |r| {
                    Ok(User {
                        id: r.get(0)?,
                        username: r.get(1)?,
                        role: r.get(2)?,
                        created_at: r.get(3)?,
                    })
                },
            )
            .optional()?
            .ok_or_else(|| AppError::Auth("用户不存在".into()))
    }

    fn issue_session(&self, user: User) -> Result<Session> {
        let token = Uuid::new_v4().to_string();
        let now = Utc::now().timestamp();
        self.db.conn().execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?1, ?2, ?3, ?4)",
            params![token, user.id, now, now + SESSION_TTL_SECS],
        )?;
        Ok(Session { token, user })
    }
}

fn hash_password(password: &str) -> Result<String> {
    let salt = SaltString::generate(&mut OsRng);
    let hash = Argon2::default()
        .hash_password(password.as_bytes(), &salt)
        .map_err(|e| AppError::Auth(e.to_string()))?
        .to_string();
    Ok(hash)
}

fn verify_password(password: &str, hash: &str) -> bool {
    let Ok(parsed) = PasswordHash::new(hash) else { return false; };
    Argon2::default().verify_password(password.as_bytes(), &parsed).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::storage::Db;

    #[test]
    fn register_login_verify_roundtrip() {
        let db = Db::open_in_memory().unwrap();
        let auth = AuthService::new(db);
        let user = auth.register("alice", "secret123").unwrap();
        assert_eq!(user.username, "alice");
        assert!(auth.register("alice", "secret123").is_err(), "重名应失败");

        let session = auth.login("alice", "secret123").unwrap();
        let u = auth.verify_session(&session.token).unwrap();
        assert_eq!(u.id, user.id);
        assert!(auth.login("alice", "wrong").is_err(), "错误密码应失败");
        auth.logout(&session.token).unwrap();
        assert!(auth.verify_session(&session.token).is_err(), "登出后会话应失效");
    }
}

