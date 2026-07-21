use crate::db::Database;
use crate::screens::market_overview::MarketOverview;
use crate::screens::news_feed::NewsFeed;
use crate::screens::portfolio_view::PortfolioView;
use crate::screens::research::Research;
use crate::screens::stock_detail::StockDetail;
use crate::screens::{AppAction, Screen, ScreenId};
use anyhow::Result;
use crossterm::event::{self, Event, KeyEventKind};
use crossterm::terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen};
use crossterm::ExecutableCommand;
use ratatui::prelude::CrosstermBackend;
use ratatui::Terminal;
use std::io;
use std::sync::Arc;
use std::time::Duration;

pub struct App {
    db: Arc<Database>,
    current: Box<dyn Screen>,
    portfolio_id: i64,
}

impl App {
    pub fn new(db: Arc<Database>) -> Self {
        let portfolio = db
            .create_portfolio("Default", 1_000_000.0)
            .unwrap_or_else(|_| {
                db.get_portfolio(1).unwrap_or_else(|| {
                    panic!("Could not create or find portfolio")
                })
            });
        let portfolio_id = portfolio.id;
        let mo = MarketOverview::new();
        App {
            db,
            current: Box::new(mo),
            portfolio_id,
        }
    }

    pub fn switch_screen(&mut self, id: ScreenId) {
        match id {
            ScreenId::MarketOverview => {
                self.current = Box::new(MarketOverview::new());
            }
            ScreenId::StockDetail(symbol) => {
                self.current = Box::new(StockDetail::new(symbol));
            }
            ScreenId::Portfolio => {
                self.current = Box::new(PortfolioView::new(self.db.clone(), self.portfolio_id));
            }
            ScreenId::News => {
                self.current = Box::new(NewsFeed::new());
            }
            ScreenId::Research => {
                self.current = Box::new(Research::new());
            }
        }
    }

    pub async fn run(&mut self) -> Result<()> {
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        stdout.execute(EnterAlternateScreen)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;
        terminal.clear()?;

        let refresh_rate = Duration::from_millis(250);
        let mut last_refresh = std::time::Instant::now();

        loop {
            terminal.draw(|f| {
                let size = f.area();
                self.current.draw(f, size);
            })?;

            if event::poll(refresh_rate)? {
                let ev = event::read()?;
                if let Event::Key(key) = ev {
                    if key.kind == KeyEventKind::Press {
                        match self.current.handle_key(key) {
                            Some(AppAction::Quit) => break,
                            Some(AppAction::Back) => {
                                self.switch_screen(ScreenId::MarketOverview);
                            }
                            Some(AppAction::SwitchScreen(id)) => {
                                self.switch_screen(id);
                            }
                            _ => {}
                        }
                    }
                }
            }

            if last_refresh.elapsed() > Duration::from_secs(30) {
                // Refresh market data periodically
                last_refresh = std::time::Instant::now();
            }
        }

        disable_raw_mode()?;
        terminal.backend_mut().execute(LeaveAlternateScreen)?;
        terminal.show_cursor()?;
        Ok(())
    }
}
