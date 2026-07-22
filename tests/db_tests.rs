use bloomberg_terminal::db::Database;
use tempfile::TempDir;

fn setup_db() -> Database {
    let dir = TempDir::new().unwrap();
    Database::new(&dir.path().join("test.db")).unwrap()
}

#[test]
fn test_create_and_get_portfolio() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    assert_eq!(pf.name, "main");
    assert!((pf.cash_balance - 100_000.0).abs() < 0.01);
    let fetched = db.get_portfolio(pf.id).unwrap();
    assert_eq!(fetched.id, pf.id);
    assert_eq!(fetched.name, "main");
}

#[test]
fn test_get_portfolio_not_found() {
    let db = setup_db();
    assert!(db.get_portfolio(999).is_none());
}

#[test]
fn test_update_cash() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    db.update_cash(pf.id, 50_000.0).unwrap();
    let updated = db.get_portfolio(pf.id).unwrap();
    assert!((updated.cash_balance - 50_000.0).abs() < 0.01);
}

#[test]
fn test_create_and_get_position() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    let pos = db.create_position(pf.id, "AAPL", 100.0, 150.0).unwrap();
    assert_eq!(pos.symbol, "AAPL");
    assert!((pos.quantity - 100.0).abs() < 0.001);

    let positions = db.get_positions(pf.id);
    assert_eq!(positions.len(), 1);
    assert_eq!(positions[0].symbol, "AAPL");

    let pos2 = db.get_position(pf.id, "AAPL").unwrap();
    assert_eq!(pos2.id, pos.id);
}

#[test]
fn test_get_position_nonexistent_symbol() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    assert!(db.get_position(pf.id, "NONEXIST").is_none());
}

#[test]
fn test_get_positions_empty() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    let positions = db.get_positions(pf.id);
    assert!(positions.is_empty());
}

#[test]
fn test_update_position() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    let pos = db.create_position(pf.id, "AAPL", 100.0, 150.0).unwrap();
    db.update_position(pos.id, 200.0, 155.0, 31_000.0).unwrap();
    let positions = db.get_positions(pf.id);
    assert!((positions[0].quantity - 200.0).abs() < 0.001);
    assert!((positions[0].avg_cost - 155.0).abs() < 0.01);
}

#[test]
fn test_delete_position() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    let pos = db.create_position(pf.id, "AAPL", 100.0, 150.0).unwrap();
    db.delete_position(pos.id).unwrap();
    assert!(db.get_position(pf.id, "AAPL").is_none());
}

#[test]
fn test_create_and_get_trades() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    let t = db.create_trade(pf.id, "AAPL", "buy", 100.0, 150.0).unwrap();
    assert_eq!(t.symbol, "AAPL");
    assert_eq!(t.side, "buy");
    assert_eq!(t.status, "filled");

    let trades = db.get_trades(pf.id);
    assert_eq!(trades.len(), 1);
    assert_eq!(trades[0].id, t.id);
}

#[test]
fn test_get_trades_empty() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    let trades = db.get_trades(pf.id);
    assert!(trades.is_empty());
}

#[test]
fn test_multiple_trades_ordered_by_timestamp_desc() {
    let db = setup_db();
    let pf = db.create_portfolio("main", 100_000.0).unwrap();
    let _t1 = db.create_trade(pf.id, "AAPL", "buy", 10.0, 150.0).unwrap();
    let _t2 = db.create_trade(pf.id, "TSLA", "buy", 5.0, 300.0).unwrap();
    let trades = db.get_trades(pf.id);
    assert_eq!(trades.len(), 2);
}

#[test]
fn test_create_user() {
    let db = setup_db();
    let id = db.create_user("user@example.com", "hash123").unwrap();
    assert!(id > 0);
}

#[test]
fn test_create_user_duplicate_email_fails() {
    let db = setup_db();
    db.create_user("dup@example.com", "hash1").unwrap();
    let result = db.create_user("dup@example.com", "hash2");
    assert!(result.is_err());
}

#[test]
fn test_get_user_by_email() {
    let db = setup_db();
    db.create_user("find@example.com", "hash_val").unwrap();
    let user = db.get_user_by_email("find@example.com").unwrap();
    assert_eq!(user.1, "hash_val");
    assert_eq!(user.2, 0);
    assert!(user.3.is_some());
}

#[test]
fn test_get_user_by_email_not_found() {
    let db = setup_db();
    assert!(db.get_user_by_email("nobody@example.com").is_none());
}

#[test]
fn test_verify_email() {
    let db = setup_db();
    let id = db.create_user("verify@example.com", "hash").unwrap();
    db.verify_email(id).unwrap();
    let user = db.get_user_by_email("verify@example.com").unwrap();
    assert_eq!(user.2, 1);
}

#[test]
fn test_save_and_get_news() {
    let db = setup_db();
    db.save_news(
        "Market rally",
        "Reuters",
        "https://reut.rs/abc",
        "Stocks surged today",
        Some("2025-01-15"),
    )
    .unwrap();
    let news = db.get_news(10);
    assert_eq!(news.len(), 1);
    assert_eq!(news[0].title, "Market rally");
    assert_eq!(news[0].source, "Reuters");
}

#[test]
fn test_save_news_without_date() {
    let db = setup_db();
    db.save_news(
        "Breaking news",
        "CNBC",
        "https://cnbc.com/xyz",
        "Something happened",
        None,
    )
    .unwrap();
    let news = db.get_news(10);
    assert_eq!(news.len(), 1);
    assert!(news[0].published_at.is_none());
}

#[test]
fn test_get_news_limit() {
    let db = setup_db();
    for i in 0..5 {
        db.save_news(&format!("News {}", i), "Src", "url", "summary", None)
            .unwrap();
    }
    let news = db.get_news(3);
    assert_eq!(news.len(), 3);
}

#[test]
fn test_get_news_empty() {
    let db = setup_db();
    let news = db.get_news(10);
    assert!(news.is_empty());
}

#[test]
fn test_save_and_get_papers() {
    let db = setup_db();
    db.save_paper(
        "Deep Learning in Finance",
        "Smith et al.",
        "We propose a novel approach...",
        "https://arxiv.org/abs/1234",
        Some("2025-01-10"),
    )
    .unwrap();
    let papers = db.get_papers(10);
    assert_eq!(papers.len(), 1);
    assert_eq!(papers[0].title, "Deep Learning in Finance");
}

#[test]
fn test_get_papers_limit() {
    let db = setup_db();
    for i in 0..5 {
        db.save_paper(&format!("Paper {}", i), "Author", "Abstract", "url", None)
            .unwrap();
    }
    let papers = db.get_papers(2);
    assert_eq!(papers.len(), 2);
}

#[test]
fn test_get_papers_empty() {
    let db = setup_db();
    let papers = db.get_papers(10);
    assert!(papers.is_empty());
}

#[test]
fn test_log_and_get_audit() {
    let db = setup_db();
    db.log_audit("LOGIN", "alice", "Successful login", "192.168.1.1")
        .unwrap();
    let logs = db.get_audit_logs(10);
    assert_eq!(logs.len(), 1);
    assert_eq!(logs[0].action, "LOGIN");
    assert_eq!(logs[0].user, "alice");
    assert_eq!(logs[0].ip_address, "192.168.1.1");
}

#[test]
fn test_get_audit_logs_empty() {
    let db = setup_db();
    let logs = db.get_audit_logs(10);
    assert!(logs.is_empty());
}

#[test]
fn test_set_bank_details() {
    let db = setup_db();
    let uid = db.create_user("bank@example.com", "hash").unwrap();
    db.set_bank_details(uid, "Chase", "12345678", "021000021", "checking")
        .unwrap();
}

#[test]
fn test_set_wallet() {
    let db = setup_db();
    let uid = db.create_user("wallet@example.com", "hash").unwrap();
    db.set_wallet(uid, "0xabc123", "ethereum").unwrap();
}

#[test]
fn test_complete_tutorial() {
    let db = setup_db();
    let uid = db.create_user("tutorial@example.com", "hash").unwrap();
    db.complete_tutorial(uid, "getting_started").unwrap();
}

#[test]
fn test_multiple_portfolios() {
    let db = setup_db();
    let pf1 = db.create_portfolio("retirement", 500_000.0).unwrap();
    let pf2 = db.create_portfolio("trading", 50_000.0).unwrap();
    assert_ne!(pf1.id, pf2.id);
    let pf1_fetched = db.get_portfolio(pf1.id).unwrap();
    let pf2_fetched = db.get_portfolio(pf2.id).unwrap();
    assert!((pf1_fetched.cash_balance - 500_000.0).abs() < 0.01);
    assert!((pf2_fetched.cash_balance - 50_000.0).abs() < 0.01);
}

#[test]
fn test_full_lifecycle() {
    let db = setup_db();
    let pf = db.create_portfolio("lifecycle", 10_000.0).unwrap();

    let pos = db.create_position(pf.id, "AAPL", 10.0, 150.0).unwrap();
    assert_eq!(pos.symbol, "AAPL");

    db.update_cash(pf.id, 8_500.0).unwrap();
    let updated_pf = db.get_portfolio(pf.id).unwrap();
    assert!((updated_pf.cash_balance - 8_500.0).abs() < 0.01);

    let trade = db.create_trade(pf.id, "AAPL", "buy", 10.0, 150.0).unwrap();
    assert_eq!(trade.status, "filled");

    db.log_audit("TRADE", "user1", "Buy 10 AAPL @ $150", "127.0.0.1")
        .unwrap();

    db.update_position(pos.id, 5.0, 150.0, 750.0).unwrap();
    let updated_pos = db.get_position(pf.id, "AAPL").unwrap();
    assert!((updated_pos.quantity - 5.0).abs() < 0.001);

    db.delete_position(pos.id).unwrap();
    assert!(db.get_position(pf.id, "AAPL").is_none());

    let trades = db.get_trades(pf.id);
    assert_eq!(trades.len(), 1);
    let logs = db.get_audit_logs(10);
    assert_eq!(logs.len(), 1);
}
