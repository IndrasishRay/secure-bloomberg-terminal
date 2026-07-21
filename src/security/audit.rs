use crate::db::Database;
use anyhow::Result;
use chrono::Utc;
use log::info;

pub fn log_event(db: &Database, action: &str, user: &str, details: &str) -> Result<()> {
    let timestamp = Utc::now().format("%Y-%m-%d %H:%M:%S").to_string();
    info!("[{}] {} - {}: {}", timestamp, user, action, details);
    db.log_audit(action, user, details, "127.0.0.1")?;
    Ok(())
}
