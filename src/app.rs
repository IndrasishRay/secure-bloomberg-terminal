use crate::db::Database;
use crate::news::fetch_news;
use crate::portfolio::PortfolioManager;
use crate::research::fetch_papers;
use crate::screens::market_overview::MarketOverview;
use crate::screens::news_feed::NewsFeed;
use crate::screens::portfolio_view::PortfolioView;
use crate::screens::research::Research;
use crate::screens::stock_detail::StockDetail;
use crate::screens::{AppAction, Screen, ScreenId};
use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use crossterm::terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen};
use crossterm::ExecutableCommand;
use ratatui::prelude::CrosstermBackend;
use ratatui::Terminal;
use std::io;
use std::sync::Arc;
use std::time::Duration;

enum AppScreen {
    Market(MarketOverview),
    Stock(StockDetail),
    Portfolio(PortfolioView),
    News(NewsFeed),
    Research(Research),
}

pub struct App {
    db: Arc<Database>,
    pm: PortfolioManager,
    current: AppScreen,
}

impl App {
    pub fn new(db: Arc<Database>) -> Self {
        let portfolio = db.get_portfolio(1).unwrap_or_else(|| {
            db.create_portfolio("Default", 1_000_000.0)
                .expect("failed to create portfolio")
        });
        let portfolio_id = portfolio.id;
        let pm = PortfolioManager::new(db.clone(), portfolio_id);
        App { db, pm, current: AppScreen::Market(MarketOverview::new()) }
    }

    fn switch_screen(&mut self, id: ScreenId) {
        match id {
            ScreenId::MarketOverview => {
                self.current = AppScreen::Market(MarketOverview::new());
            }
            ScreenId::StockDetail(symbol) => {
                self.current = AppScreen::Stock(StockDetail::new(symbol.clone()));
            }
            ScreenId::Portfolio => {
                self.current = AppScreen::Portfolio(PortfolioView::new(self.db.clone(), self.pm.portfolio_id));
            }
            ScreenId::News => {
                self.current = AppScreen::News(NewsFeed::new());
            }
            ScreenId::Research => {
                self.current = AppScreen::Research(Research::new());
            }
        }
    }

    async fn refresh_current(&mut self) {
        match &mut self.current {
            AppScreen::Market(m) => m.refresh().await,
            AppScreen::Stock(s) => s.refresh().await,
            AppScreen::Portfolio(p) => p.refresh(),
            _ => {}
        }
    }

    pub async fn run(&mut self) -> Result<()> {
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        stdout.execute(EnterAlternateScreen)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;
        terminal.clear()?;

        self.refresh_current().await;

        let poll_rate = Duration::from_millis(100);
        let mut last_refresh = std::time::Instant::now();

        loop {
            terminal.draw(|f| {
                let size = f.area();
                match &mut self.current {
                    AppScreen::Market(m) => m.draw(f, size),
                    AppScreen::Stock(s) => s.draw(f, size),
                    AppScreen::Portfolio(p) => p.draw(f, size),
                    AppScreen::News(n) => n.draw(f, size),
                    AppScreen::Research(r) => r.draw(f, size),
                }
            })?;

            if event::poll(poll_rate)? {
                let ev = event::read()?;
                if let Event::Key(key) = ev {
                    if key.kind == KeyEventKind::Press {
                        match key.code {
                            KeyCode::Char('1') => {
                                self.switch_screen(ScreenId::MarketOverview);
                                self.refresh_current().await;
                                continue;
                            }
                            KeyCode::Char('3') => {
                                self.switch_screen(ScreenId::Portfolio);
                                self.pm = PortfolioManager::new(self.db.clone(), self.pm.portfolio_id);
                                self.refresh_current().await;
                                continue;
                            }
                            KeyCode::Char('4') => {
                                self.switch_screen(ScreenId::News);
                                let articles = fetch_news().await;
                                if let AppScreen::News(ref mut n) = self.current {
                                    n.set_articles(articles);
                                }
                                continue;
                            }
                            KeyCode::Char('5') => {
                                self.switch_screen(ScreenId::Research);
                                let papers = fetch_papers().await;
                                if let AppScreen::Research(ref mut r) = self.current {
                                    r.set_papers(papers);
                                }
                                continue;
                            }
                            _ => {}
                        }

                        let action = match &mut self.current {
                            AppScreen::Market(m) => m.handle_key(key),
                            AppScreen::Stock(s) => s.handle_key(key),
                            AppScreen::Portfolio(p) => p.handle_key(key),
                            AppScreen::News(n) => n.handle_key(key),
                            AppScreen::Research(r) => r.handle_key(key),
                        };

                        match action {
                            Some(AppAction::Quit) => break,
                            Some(AppAction::Back) => {
                                self.switch_screen(ScreenId::MarketOverview);
                                self.refresh_current().await;
                            }
                            Some(AppAction::SwitchScreen(id)) => {
                                self.switch_screen(id);
                                self.refresh_current().await;
                            }
                            Some(AppAction::Buy(sym)) => {
                                if let AppScreen::Stock(ref mut s) = self.current {
                                    if let Some(price) = s.current_price() {
                                        let qty = s.buy_qty();
                                        if qty > 0.0 {
                                            match self.pm.buy(&sym, qty, price) {
                                                Ok(_t) => {
                                                    s.set_message(format!("Bought {:.2} {} @ ${:.2}", qty, sym, price));
                                                    self.refresh_current().await;
                                                }
                                                Err(e) => s.set_message(format!("Buy failed: {}", e)),
                                            }
                                        }
                                    }
                                }
                            }
                            Some(AppAction::Sell(sym)) => {
                                if let AppScreen::Stock(ref mut s) = self.current {
                                    if let Some(price) = s.current_price() {
                                        let qty = s.sell_qty();
                                        if qty > 0.0 {
                                            match self.pm.sell(&sym, qty, price) {
                                                Ok(_t) => {
                                                    s.set_message(format!("Sold {:.2} {} @ ${:.2}", qty, sym, price));
                                                    self.refresh_current().await;
                                                }
                                                Err(e) => s.set_message(format!("Sell failed: {}", e)),
                                            }
                                        }
                                    }
                                }
                            }
                            _ => {}
                        }
                    }
                }
            }

            if last_refresh.elapsed() > Duration::from_secs(30) {
                self.refresh_current().await;
                last_refresh = std::time::Instant::now();
            }
        }

        disable_raw_mode()?;
        terminal.backend_mut().execute(LeaveAlternateScreen)?;
        terminal.show_cursor()?;
        Ok(())
    }
}
