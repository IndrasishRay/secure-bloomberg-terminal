use anyhow::Result;
use bloomberg_terminal::app::App;
use bloomberg_terminal::db::Database;
use bloomberg_terminal::onboarding::wizard::run_onboarding;
use bloomberg_terminal::security::encryption::Crypto;
use std::path::Path;
use std::sync::Arc;

#[tokio::main]
async fn main() -> Result<()> {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let data_dir = dirs::data_dir()
        .unwrap_or_else(|| Path::new(".").to_path_buf())
        .join("bloomberg-terminal");

    let db_path = data_dir.join("terminal.db");
    let key_path = data_dir.join("terminal.key");

    std::fs::create_dir_all(&data_dir)?;

    let db = Arc::new(Database::new(&db_path)?);
    let crypto = Crypto::new(&key_path)?;

    log::info!("Database initialized at {:?}", db_path);
    log::info!("Starting Secure Bloomberg Terminal");

    let onboarding_ok = run_onboarding(&db, &crypto)?;
    if !onboarding_ok {
        log::warn!("Onboarding cancelled");
        return Ok(());
    }

    let mut terminal_app = App::new(db);
    terminal_app.run().await?;

    log::info!("Bloomberg Terminal terminated");
    Ok(())
}
