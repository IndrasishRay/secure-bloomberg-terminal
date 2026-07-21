use anyhow::Result;
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Portfolio {
    pub id: i64,
    pub name: String,
    pub cash_balance: f64,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub id: i64,
    pub portfolio_id: i64,
    pub symbol: String,
    pub quantity: f64,
    pub avg_cost: f64,
    pub current_value: f64,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    pub id: i64,
    pub portfolio_id: i64,
    pub symbol: String,
    pub side: String,
    pub quantity: f64,
    pub price: f64,
    pub status: String,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewsArticle {
    pub id: i64,
    pub title: String,
    pub source: String,
    pub url: String,
    pub summary: String,
    pub published_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchPaper {
    pub id: i64,
    pub title: String,
    pub authors: String,
    pub abstract_: String,
    pub url: String,
    pub published_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditLog {
    pub id: i64,
    pub action: String,
    pub user: String,
    pub details: String,
    pub ip_address: String,
    pub timestamp: String,
}

pub struct Database {
    conn: Mutex<Connection>,
}

impl Database {
    pub fn new(path: &Path) -> Result<Self> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let conn = Connection::open(path)?;
        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")?;
        let db = Database {
            conn: Mutex::new(conn),
        };
        db.initialize()?;
        Ok(db)
    }

    fn initialize(&self) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cash_balance REAL DEFAULT 0.0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                avg_cost REAL NOT NULL,
                current_value REAL NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'filled',
                timestamp TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT DEFAULT '',
                url TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                published_at TEXT
            );
            CREATE TABLE IF NOT EXISTS research_papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT DEFAULT '',
                abstract_ TEXT DEFAULT '',
                url TEXT DEFAULT '',
                published_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                user TEXT DEFAULT 'system',
                details TEXT DEFAULT '',
                ip_address TEXT DEFAULT '127.0.0.1',
                timestamp TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email_verified INTEGER DEFAULT 0,
                verification_code TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS bank_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                bank_name TEXT NOT NULL,
                account_number TEXT NOT NULL,
                routing_number TEXT NOT NULL,
                account_type TEXT DEFAULT 'checking',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                address TEXT NOT NULL,
                wallet_type TEXT DEFAULT 'other',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS tutorial_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                tutorial_id TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                completed_at TEXT
            );
            ",
        )?;
        Ok(())
    }

    // Users
    pub fn create_user(&self, email: &str, password_hash: &str) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO users (email, password_hash, verification_code) VALUES (?1, ?2, ?3)",
            params![email, password_hash, Self::generate_code()],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn get_user_by_email(&self, email: &str) -> Option<(i64, String, i64, Option<String>)> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT id, password_hash, email_verified, verification_code FROM users WHERE email = ?1")
            .ok()?;
        stmt.query_row(params![email], |row| {
            Ok((
                row.get(0)?,
                row.get(1)?,
                row.get(2)?,
                row.get(3)?,
            ))
        })
        .ok()
    }

    pub fn verify_email(&self, user_id: i64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE users SET email_verified = 1 WHERE id = ?1",
            params![user_id],
        )?;
        Ok(())
    }

    // Bank
    pub fn set_bank_details(&self, user_id: i64, name: &str, acct: &str, routing: &str, acct_type: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO bank_details (user_id, bank_name, account_number, routing_number, account_type) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![user_id, name, acct, routing, acct_type],
        )?;
        Ok(())
    }

    // Wallet
    pub fn set_wallet(&self, user_id: i64, address: &str, wallet_type: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO wallets (user_id, address, wallet_type) VALUES (?1, ?2, ?3)",
            params![user_id, address, wallet_type],
        )?;
        Ok(())
    }

    // Tutorial
    pub fn complete_tutorial(&self, user_id: i64, tutorial_id: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO tutorial_progress (user_id, tutorial_id, completed, completed_at) VALUES (?1, ?2, 1, datetime('now'))",
            params![user_id, tutorial_id],
        )?;
        Ok(())
    }

    // Portfolio
    pub fn create_portfolio(&self, name: &str, cash: f64) -> Result<Portfolio> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO portfolios (name, cash_balance) VALUES (?1, ?2)",
            params![name, cash],
        )?;
        let id = conn.last_insert_rowid();
        let mut stmt = conn.prepare("SELECT * FROM portfolios WHERE id = ?1")?;
        let p = stmt.query_row(params![id], |row| {
            Ok(Portfolio {
                id: row.get(0)?,
                name: row.get(1)?,
                cash_balance: row.get(2)?,
                created_at: row.get(3)?,
                updated_at: row.get(4)?,
            })
        })?;
        Ok(p)
    }

    pub fn get_portfolio(&self, id: i64) -> Option<Portfolio> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT * FROM portfolios WHERE id = ?1").ok()?;
        stmt.query_row(params![id], |row| {
            Ok(Portfolio {
                id: row.get(0)?,
                name: row.get(1)?,
                cash_balance: row.get(2)?,
                created_at: row.get(3)?,
                updated_at: row.get(4)?,
            })
        })
        .ok()
    }

    pub fn update_cash(&self, portfolio_id: i64, cash: f64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE portfolios SET cash_balance = ?1, updated_at = datetime('now') WHERE id = ?2",
            params![cash, portfolio_id],
        )?;
        Ok(())
    }

    // Positions
    pub fn create_position(&self, portfolio_id: i64, symbol: &str, qty: f64, cost: f64) -> Result<Position> {
        let conn = self.conn.lock().unwrap();
        let val = (qty * cost * 100.0).round() / 100.0;
        conn.execute(
            "INSERT INTO positions (portfolio_id, symbol, quantity, avg_cost, current_value) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![portfolio_id, symbol, qty, cost, val],
        )?;
        let id = conn.last_insert_rowid();
        let mut stmt = conn.prepare("SELECT * FROM positions WHERE id = ?1")?;
        let p = stmt.query_row(params![id], |row| {
            Ok(Position {
                id: row.get(0)?,
                portfolio_id: row.get(1)?,
                symbol: row.get(2)?,
                quantity: row.get(3)?,
                avg_cost: row.get(4)?,
                current_value: row.get(5)?,
                created_at: row.get(6)?,
                updated_at: row.get(7)?,
            })
        })?;
        Ok(p)
    }

    pub fn get_positions(&self, portfolio_id: i64) -> Vec<Position> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT * FROM positions WHERE portfolio_id = ?1 ORDER BY symbol")
            .unwrap();
        stmt.query_map(params![portfolio_id], |row| {
            Ok(Position {
                id: row.get(0)?,
                portfolio_id: row.get(1)?,
                symbol: row.get(2)?,
                quantity: row.get(3)?,
                avg_cost: row.get(4)?,
                current_value: row.get(5)?,
                created_at: row.get(6)?,
                updated_at: row.get(7)?,
            })
        })
        .unwrap()
        .filter_map(|r| r.ok())
        .collect()
    }

    pub fn get_position(&self, portfolio_id: i64, symbol: &str) -> Option<Position> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT * FROM positions WHERE portfolio_id = ?1 AND symbol = ?2")
            .ok()?;
        stmt.query_row(params![portfolio_id, symbol], |row| {
            Ok(Position {
                id: row.get(0)?,
                portfolio_id: row.get(1)?,
                symbol: row.get(2)?,
                quantity: row.get(3)?,
                avg_cost: row.get(4)?,
                current_value: row.get(5)?,
                created_at: row.get(6)?,
                updated_at: row.get(7)?,
            })
        })
        .ok()
    }

    pub fn update_position(&self, id: i64, qty: f64, cost: f64, val: f64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE positions SET quantity = ?1, avg_cost = ?2, current_value = ?3, updated_at = datetime('now') WHERE id = ?4",
            params![qty, cost, val, id],
        )?;
        Ok(())
    }

    pub fn delete_position(&self, id: i64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM positions WHERE id = ?1", params![id])?;
        Ok(())
    }

    // Trades
    pub fn create_trade(&self, portfolio_id: i64, symbol: &str, side: &str, qty: f64, price: f64) -> Result<Trade> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO trades (portfolio_id, symbol, side, quantity, price, status) VALUES (?1, ?2, ?3, ?4, ?5, 'filled')",
            params![portfolio_id, symbol, side, qty, price],
        )?;
        let id = conn.last_insert_rowid();
        let mut stmt = conn.prepare("SELECT * FROM trades WHERE id = ?1")?;
        let t = stmt.query_row(params![id], |row| {
            Ok(Trade {
                id: row.get(0)?,
                portfolio_id: row.get(1)?,
                symbol: row.get(2)?,
                side: row.get(3)?,
                quantity: row.get(4)?,
                price: row.get(5)?,
                status: row.get(6)?,
                timestamp: row.get(7)?,
            })
        })?;
        Ok(t)
    }

    pub fn get_trades(&self, portfolio_id: i64) -> Vec<Trade> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT * FROM trades WHERE portfolio_id = ?1 ORDER BY timestamp DESC")
            .unwrap();
        stmt.query_map(params![portfolio_id], |row| {
            Ok(Trade {
                id: row.get(0)?,
                portfolio_id: row.get(1)?,
                symbol: row.get(2)?,
                side: row.get(3)?,
                quantity: row.get(4)?,
                price: row.get(5)?,
                status: row.get(6)?,
                timestamp: row.get(7)?,
            })
        })
        .unwrap()
        .filter_map(|r| r.ok())
        .collect()
    }

    // News
    pub fn save_news(&self, title: &str, source: &str, url: &str, summary: &str, published: Option<&str>) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO news_articles (title, source, url, summary, published_at) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![title, source, url, summary, published],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn get_news(&self, limit: i64) -> Vec<NewsArticle> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT * FROM news_articles ORDER BY published_at DESC LIMIT ?1")
            .unwrap();
        stmt.query_map(params![limit], |row| {
            Ok(NewsArticle {
                id: row.get(0)?,
                title: row.get(1)?,
                source: row.get(2)?,
                url: row.get(3)?,
                summary: row.get(4)?,
                published_at: row.get(5)?,
            })
        })
        .unwrap()
        .filter_map(|r| r.ok())
        .collect()
    }

    // Research
    pub fn save_paper(&self, title: &str, authors: &str, abstract_: &str, url: &str, published: Option<&str>) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO research_papers (title, authors, abstract_, url, published_at) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![title, authors, abstract_, url, published],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn get_papers(&self, limit: i64) -> Vec<ResearchPaper> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT * FROM research_papers ORDER BY published_at DESC LIMIT ?1")
            .unwrap();
        stmt.query_map(params![limit], |row| {
            Ok(ResearchPaper {
                id: row.get(0)?,
                title: row.get(1)?,
                authors: row.get(2)?,
                abstract_: row.get(3)?,
                url: row.get(4)?,
                published_at: row.get(5)?,
            })
        })
        .unwrap()
        .filter_map(|r| r.ok())
        .collect()
    }

    // Audit
    pub fn log_audit(&self, action: &str, user: &str, details: &str, ip: &str) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO audit_logs (action, user, details, ip_address) VALUES (?1, ?2, ?3, ?4)",
            params![action, user, details, ip],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn get_audit_logs(&self, limit: i64) -> Vec<AuditLog> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?1")
            .unwrap();
        stmt.query_map(params![limit], |row| {
            Ok(AuditLog {
                id: row.get(0)?,
                action: row.get(1)?,
                user: row.get(2)?,
                details: row.get(3)?,
                ip_address: row.get(4)?,
                timestamp: row.get(5)?,
            })
        })
        .unwrap()
        .filter_map(|r| r.ok())
        .collect()
    }

    fn generate_code() -> String {
        use rand::Rng;
        let mut rng = rand::thread_rng();
        (0..6).map(|_| rng.gen_range(0..10).to_string()).collect()
    }
}
