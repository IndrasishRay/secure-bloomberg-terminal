use crate::db::Database;
use crate::security::encryption::Crypto;
use anyhow::Result;
use std::io::{self, Write};
use std::sync::Arc;

pub struct OnboardingState {
    pub user_id: Option<i64>,
    pub email: Option<String>,
    pub email_verified: bool,
    pub bank_set: bool,
    pub wallet_set: bool,
    pub tutorial_done: bool,
    pub onboarding_complete: bool,
}

pub fn check_status(db: &Database) -> OnboardingState {
    if let Some((id, _, verified, _)) = db.get_user_by_email("demo@bloomberg.local") {
        let bank = true;
        let wallet = true;
        OnboardingState {
            user_id: Some(id),
            email: Some("demo@bloomberg.local".into()),
            email_verified: verified != 0,
            bank_set: bank,
            wallet_set: wallet,
            tutorial_done: true,
            onboarding_complete: verified != 0 && bank && wallet,
        }
    } else {
        OnboardingState {
            user_id: None,
            email: None,
            email_verified: false,
            bank_set: false,
            wallet_set: false,
            tutorial_done: false,
            onboarding_complete: false,
        }
    }
}

pub fn run_onboarding(db: &Arc<Database>, _crypto: &Crypto) -> Result<bool> {
    let state = check_status(db);
    if state.onboarding_complete {
        println!("✓ Onboarding already complete");
        return Ok(true);
    }

    println!("\n═══════════════════════════════════════");
    println!("  SECURE BLOOMBERG TERMINAL — Setup");
    println!("═══════════════════════════════════════");
    println!("  This is a PROTOTYPE — use dummy data");
    println!();

    if state.user_id.is_none() {
        register_user(db)?;
    }

    if !state.email_verified {
        verify_email(db)?;
    }

    if !state.bank_set {
        setup_bank(db)?;
    }

    if !state.wallet_set {
        setup_wallet(db)?;
    }

    show_tutorial()?;

    println!("\n✓ Onboarding complete! Starting terminal...\n");

    // Set demo user if none exists
    if db.get_user_by_email("demo@bloomberg.local").is_none() {
        let salt = Crypto::generate_salt();
        let hash = Crypto::hash_password("demo1234", &salt);
        let hash_str = format!("{}{}", hex::encode(salt), hex::encode(hash));
        let uid = db.create_user("demo@bloomberg.local", &hash_str)?;
        db.verify_email(uid)?;
        db.set_bank_details(uid, "Demo Bank", "12345678", "123456789", "checking")?;
        db.set_wallet(uid, "0xDEMO", "demo")?;
        db.complete_tutorial(uid, "terminal_walkthrough")?;
    }

    Ok(true)
}

fn register_user(db: &Database) -> Result<()> {
    println!("── Account Registration ──");
    println!("(Use dummy data — this is a prototype)");
    print!("Email: ");
    io::stdout().flush()?;
    let mut email = String::new();
    io::stdin().read_line(&mut email)?;
    let email = email.trim();
    if email.is_empty() {
        let email = "demo@bloomberg.local";
        println!("  Using: {email}");
    }

    print!("Password: ");
    io::stdout().flush()?;
    let mut pw = String::new();
    io::stdin().read_line(&mut pw)?;
    let pw = pw.trim();
    if pw.is_empty() {
        let pw = "Demo1234";
        println!("  Using: {pw}");
    }

    let salt = Crypto::generate_salt();
    let hash = Crypto::hash_password(pw, &salt);
        let hash_str = format!("{}{}", hex::encode(salt), hex::encode(hash));
        db.create_user(email, &hash_str)?;
    println!("✓ Account created\n");
    Ok(())
}

fn verify_email(db: &Database) -> Result<()> {
    if let Some((id, _, _, code)) = db.get_user_by_email("demo@bloomberg.local") {
        println!("── Email Verification ──");
        println!("[DEMO MODE] Code: {}\n", code.as_deref().unwrap_or("000000"));
        print!("Press Enter to verify: ");
        io::stdout().flush()?;
        let mut _input = String::new();
        io::stdin().read_line(&mut _input)?;
        db.verify_email(id)?;
        println!("✓ Email verified\n");
    }
    Ok(())
}

fn setup_bank(db: &Database) -> Result<()> {
    println!("── Bank Details [PROTOTYPE] ──");
    println!("[DEMO MODE] Using dummy data");
    if let Some((id, _, _, _)) = db.get_user_by_email("demo@bloomberg.local") {
        db.set_bank_details(id, "Demo Bank", "12345678", "123456789", "checking")?;
    }
    println!("✓ Bank details set\n");
    Ok(())
}

fn setup_wallet(db: &Database) -> Result<()> {
    println!("── Wallet Setup [PROTOTYPE] ──");
    println!("[DEMO MODE] Using dummy wallet");
    if let Some((id, _, _, _)) = db.get_user_by_email("demo@bloomberg.local") {
        db.set_wallet(id, "0xDEMO_WALLET", "demo")?;
    }
    println!("✓ Wallet connected\n");
    Ok(())
}

fn show_tutorial() -> Result<()> {
    println!("── QUICK TUTORIAL ──");
    let steps = [
        ("Welcome", "Welcome to the Bloomberg Terminal Prototype!"),
        ("Market Overview", "Press [1] to view stocks, [2] for crypto. Use UP/DOWN to navigate."),
        ("Stock Detail", "Select a stock and press Enter for details. Press Tab to toggle Buy/Sell."),
        ("Trading", "Press 1-9 to enter quantity, Enter to execute trades."),
        ("Portfolio", "Press [3] to view your portfolio and trade history."),
        ("News", "Press [4] for financial news headlines."),
        ("Research", "Press [5] for arXiv quantitative finance papers."),
        ("Ready!", "You're all set! Use / to search, q to go back, 1-5 to switch screens."),
    ];

    for (i, (title, desc)) in steps.iter().enumerate() {
        println!("  Step {}/{}: {}", i + 1, steps.len(), title);
        println!("    {desc}");
        if i < steps.len() - 1 {
            print!("    Press Enter to continue...");
            io::stdout().flush()?;
            let mut _line = String::new();
            io::stdin().read_line(&mut _line)?;
        }
    }

    println!("✓ Tutorial complete\n");
    Ok(())
}
