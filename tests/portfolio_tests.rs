use bloomberg_terminal::db::Database;
use bloomberg_terminal::portfolio::PortfolioManager;
use std::sync::Arc;
use tempfile::TempDir;

fn setup_db() -> Arc<Database> {
    let dir = TempDir::new().unwrap();
    Arc::new(Database::new(&dir.path().join("test.db")).unwrap())
}

fn setup_portfolio(db: &Arc<Database>, cash: f64) -> PortfolioManager {
    let pf = db.create_portfolio("test", cash).unwrap();
    PortfolioManager::new(db.clone(), pf.id)
}

fn setup() -> PortfolioManager {
    let db = setup_db();
    setup_portfolio(&db, 100_000.0)
}

#[test]
fn test_buy_full_lifecycle() {
    let pm = setup();
    let trade = pm.buy("ZZ_1", 10.0, 150.0).unwrap();
    assert_eq!(trade.symbol, "ZZ_1");
    assert_eq!(trade.side, "buy");
    assert!((trade.quantity - 10.0).abs() < 0.0001);
    assert!((trade.price - 150.0).abs() < 0.01);

    let pf = pm.get_portfolio().unwrap();
    assert!((pf.cash_balance - 98_500.0).abs() < 0.01);

    let positions = pm.get_positions();
    assert_eq!(positions.len(), 1);
    assert_eq!(positions[0].symbol, "ZZ_1");
    assert!((positions[0].quantity - 10.0).abs() < 0.001);
}

#[test]
fn test_sell_full_lifecycle() {
    let pm = setup();
    pm.buy("ZZ_2", 10.0, 150.0).unwrap();
    let trade = pm.sell("ZZ_2", 5.0, 160.0).unwrap();
    assert_eq!(trade.side, "sell");
    assert!((trade.quantity - 5.0).abs() < 0.0001);

    let pf = pm.get_portfolio().unwrap();
    assert!((pf.cash_balance - 99_300.0).abs() < 0.01);

    let positions = pm.get_positions();
    assert_eq!(positions.len(), 1);
    assert!((positions[0].quantity - 5.0).abs() < 0.001);
}

#[test]
fn test_sell_entire_position_removes_it() {
    let pm = setup();
    pm.buy("ZZ_3", 10.0, 150.0).unwrap();
    pm.sell("ZZ_3", 10.0, 155.0).unwrap();
    let positions = pm.get_positions();
    assert!(positions.is_empty());
}

#[test]
fn test_buy_then_sell_then_buy_again() {
    let pm = setup();
    pm.buy("ZZ_4", 10.0, 150.0).unwrap();
    pm.sell("ZZ_4", 10.0, 155.0).unwrap();
    let trade = pm.buy("ZZ_4", 20.0, 152.0).unwrap();
    assert_eq!(trade.symbol, "ZZ_4");

    let positions = pm.get_positions();
    assert_eq!(positions.len(), 1);
    assert!((positions[0].quantity - 20.0).abs() < 0.001);
}

#[test]
fn test_buy_multiple_symbols() {
    let pm = setup();
    pm.buy("ZZ_5", 10.0, 150.0).unwrap();
    pm.buy("ZZ_6", 5.0, 300.0).unwrap();
    pm.buy("ZZ_7", 8.0, 140.0).unwrap();

    let positions = pm.get_positions();
    assert_eq!(positions.len(), 3);
    let symbols: Vec<String> = positions.iter().map(|p| p.symbol.clone()).collect();
    assert!(symbols.contains(&"ZZ_5".to_string()));
    assert!(symbols.contains(&"ZZ_6".to_string()));
    assert!(symbols.contains(&"ZZ_7".to_string()));
}

#[test]
fn test_buy_updates_weighted_avg_cost() {
    let pm = setup();
    pm.buy("ZZ_8", 10.0, 100.0).unwrap();
    pm.buy("ZZ_8", 10.0, 200.0).unwrap();
    let positions = pm.get_positions();
    assert!((positions[0].avg_cost - 150.0).abs() < 0.01);
    assert!((positions[0].quantity - 20.0).abs() < 0.001);
}

#[test]
fn test_trade_history() {
    let pm = setup();
    pm.buy("ZZ_9", 10.0, 150.0).unwrap();
    pm.sell("ZZ_9", 5.0, 160.0).unwrap();
    pm.buy("ZZ_A", 3.0, 300.0).unwrap();

    let trades = pm.get_trades();
    assert_eq!(trades.len(), 3);
}

#[test]
fn test_buy_insufficient_funds() {
    let db = setup_db();
    let pf = db.create_portfolio("low", 100.0).unwrap();
    let pm = PortfolioManager::new(db, pf.id);
    let err = pm.buy("ZZ_B", 10.0, 200.0).unwrap_err();
    assert!(err.to_string().contains("position would be"));
}

#[test]
fn test_sell_without_position_fails() {
    let pm = setup();
    let err = pm.sell("ZZ_NONEXIST", 10.0, 100.0).unwrap_err();
    assert!(err.to_string().contains("position not found"));
}

#[test]
fn test_sell_excessive_shares_fails() {
    let pm = setup();
    pm.buy("ZZ_C", 10.0, 150.0).unwrap();
    let err = pm.sell("ZZ_C", 20.0, 150.0).unwrap_err();
    assert!(err.to_string().contains("insufficient shares"));
}

#[test]
fn test_audit_logs_created_on_trade() {
    let db = setup_db();
    let pm = setup_portfolio(&db, 100_000.0);
    pm.buy("ZZ_D", 10.0, 150.0).unwrap();
    pm.sell("ZZ_D", 5.0, 160.0).unwrap();
    let logs = db.get_audit_logs(10);
    assert_eq!(logs.len(), 2);
    let actions: Vec<&str> = logs.iter().map(|l| l.action.as_str()).collect();
    assert!(actions.contains(&"BUY"));
    assert!(actions.contains(&"SELL"));
}
