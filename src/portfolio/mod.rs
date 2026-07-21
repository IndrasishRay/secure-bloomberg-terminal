pub mod risk_guard;

use crate::db::{Database, Position, Trade};
use crate::security::audit;
use anyhow::Result;

pub struct PortfolioManager {
    pub portfolio_id: i64,
    pub db: std::sync::Arc<Database>,
}

impl PortfolioManager {
    pub fn new(db: std::sync::Arc<Database>, portfolio_id: i64) -> Self {
        PortfolioManager { db, portfolio_id }
    }

    pub fn buy(&self, symbol: &str, quantity: f64, price: f64) -> Result<Trade> {
        let total = quantity * price;
        let mut portfolio = self.db.get_portfolio(self.portfolio_id)
            .ok_or_else(|| anyhow::anyhow!("portfolio not found"))?;

        risk_guard::check_order(&portfolio, symbol, quantity, price, "buy")?;

        if total > portfolio.cash_balance {
            anyhow::bail!("insufficient funds: need {total:.2}, have {:.2}", portfolio.cash_balance);
        }

        portfolio.cash_balance -= total;
        self.db.update_cash(self.portfolio_id, portfolio.cash_balance)?;

        let position = self.db.get_position(self.portfolio_id, symbol);
        match position {
            Some(p) => {
                let new_qty = p.quantity + quantity;
                let new_cost = ((p.avg_cost * p.quantity) + (price * quantity)) / new_qty;
                let new_val = new_qty * price;
                self.db.update_position(p.id, new_qty, new_cost, new_val)?;
            }
            None => {
                self.db.create_position(self.portfolio_id, symbol, quantity, price)?;
            }
        }

        let trade = self.db.create_trade(self.portfolio_id, symbol, "buy", quantity, price)?;
        audit::log_event(&self.db, "BUY", "user", &format!("{} {} @ ${:.2}", quantity, symbol, price)).ok();
        Ok(trade)
    }

    pub fn sell(&self, symbol: &str, quantity: f64, price: f64) -> Result<Trade> {
        let mut portfolio = self.db.get_portfolio(self.portfolio_id)
            .ok_or_else(|| anyhow::anyhow!("portfolio not found"))?;

        risk_guard::check_order(&portfolio, symbol, quantity, price, "sell")?;

        let position = self.db.get_position(self.portfolio_id, symbol)
            .ok_or_else(|| anyhow::anyhow!("position not found for {symbol}"))?;

        if quantity > position.quantity {
            anyhow::bail!("insufficient shares: have {:.2}, want {quantity:.2}", position.quantity);
        }

        let proceeds = quantity * price;
        portfolio.cash_balance += proceeds;
        self.db.update_cash(self.portfolio_id, portfolio.cash_balance)?;

        let remaining = position.quantity - quantity;
        if remaining < 0.0001 {
            self.db.delete_position(position.id)?;
        } else {
            let val = remaining * price;
            self.db.update_position(position.id, remaining, position.avg_cost, val)?;
        }

        let trade = self.db.create_trade(self.portfolio_id, symbol, "sell", quantity, price)?;
        audit::log_event(&self.db, "SELL", "user", &format!("{} {} @ ${:.2}", quantity, symbol, price)).ok();
        Ok(trade)
    }

    pub fn get_positions(&self) -> Vec<Position> {
        self.db.get_positions(self.portfolio_id)
    }

    pub fn get_trades(&self) -> Vec<Trade> {
        self.db.get_trades(self.portfolio_id)
    }

    pub fn get_portfolio(&self) -> Option<crate::db::Portfolio> {
        self.db.get_portfolio(self.portfolio_id)
    }
}
