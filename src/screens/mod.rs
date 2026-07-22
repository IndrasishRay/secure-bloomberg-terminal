pub mod market_overview;
pub mod news_feed;
pub mod portfolio_view;
pub mod research;
pub mod stock_detail;

use ratatui::layout::Rect;
use ratatui::Frame;

pub trait Screen {
    fn draw(&mut self, f: &mut Frame, area: Rect);
    fn handle_key(&mut self, key: crossterm::event::KeyEvent) -> Option<AppAction>;
}

#[derive(Debug, Clone, PartialEq)]
pub enum AppAction {
    Quit,
    SwitchScreen(ScreenId),
    Search,
    Back,
    Buy(String),
    Sell(String),
    None,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ScreenId {
    MarketOverview,
    StockDetail(String),
    Portfolio,
    News,
    Research,
}
