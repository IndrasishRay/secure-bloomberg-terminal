use crate::market::{get_top_crypto, get_top_stocks, CryptoQuote, StockQuote};
use crate::screens::{AppAction, Screen, ScreenId};
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Paragraph, Table, TableState};
use ratatui::Frame;

pub struct MarketOverview {
    stocks: Vec<StockQuote>,
    crypto: Vec<CryptoQuote>,
    state: TableState,
    tab: usize,
    loading: bool,
    error: Option<String>,
}

impl MarketOverview {
    pub fn new() -> Self {
        MarketOverview {
            stocks: Vec::new(),
            crypto: Vec::new(),
            state: TableState::default(),
            tab: 0,
            loading: true,
            error: None,
        }
    }

    pub async fn refresh(&mut self) {
        self.loading = true;
        let (stocks, crypto) = tokio::join!(get_top_stocks(), get_top_crypto());
        self.stocks = stocks;
        self.crypto = crypto;
        self.loading = false;
    }
}

impl Screen for MarketOverview {
    fn draw(&mut self, f: &mut Frame, area: Rect) {
        let title = if self.loading {
            " MARKET OVERVIEW [loading...] "
        } else {
            " MARKET OVERVIEW "
        };
        let block = Block::default()
            .title(title)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(0xFF, 0xB0, 0x00)))
            .title_style(Style::default().add_modifier(Modifier::BOLD));

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(3), Constraint::Length(3), Constraint::Min(0)])
            .split(area);

        let tabs = Paragraph::new(Line::from(vec![
            Span::styled(" [1] Stocks ", Style::default().fg(if self.tab == 0 { Color::Rgb(0xFF, 0xB0, 0x00) } else { Color::Green })),
            Span::raw(" | "),
            Span::styled(" [2] Crypto ", Style::default().fg(if self.tab == 1 { Color::Rgb(0xFF, 0xB0, 0x00) } else { Color::Green })),
        ]))
        .block(Block::default().borders(Borders::NONE));

        f.render_widget(tabs, chunks[1]);

        let inner = chunks[2];
        let header_style = Style::default()
            .fg(Color::Rgb(0xFF, 0xB0, 0x00))
            .add_modifier(Modifier::BOLD);

        if self.tab == 0 {
            let headers = ["Symbol", "Price", "Change", "Chg%", "Vol", "High", "Low"];
            let widths = [
                Constraint::Length(10),
                Constraint::Length(12),
                Constraint::Length(12),
                Constraint::Length(10),
                Constraint::Length(14),
                Constraint::Length(12),
                Constraint::Length(12),
            ];

            let rows: Vec<Vec<String>> = self
                .stocks
                .iter()
                .map(|s| {
                    vec![
                        s.symbol.clone(),
                        format!("${:.2}", s.price),
                        format!("{:.2}", s.change),
                        format!("{:.2}%", s.change_pct),
                        s.volume.to_string(),
                        format!("${:.2}", s.high),
                        format!("${:.2}", s.low),
                    ]
                })
                .collect();

            let table = Table::new(
                rows.iter().map(|r| {
                    let cells: Vec<_> = r
                        .iter()
                        .enumerate()
                        .map(|(i, c)| {
                            let color = if i == 2 || i == 3 {
                                let v: f64 = c.trim_end_matches('%').parse().unwrap_or(0.0);
                                if v >= 0.0 {
                                    Color::Green
                                } else {
                                    Color::Red
                                }
                            } else {
                                Color::Green
                            };
                            ratatui::widgets::Cell::new(Span::styled(c, Style::default().fg(color)))
                        })
                        .collect();
                    ratatui::widgets::Row::new(cells)
                }),
                widths,
            )
            .header(
                ratatui::widgets::Row::new(
                    headers.iter().map(|h| ratatui::widgets::Cell::new(Span::styled(*h, header_style))),
                )
                .height(1),
            )
            .block(Block::default().borders(Borders::NONE))
            .row_highlight_style(Style::default().bg(Color::Rgb(0x1A, 0x3A, 0x1A)));

            f.render_stateful_widget(table, inner, &mut self.state);
        } else {
            let headers = ["Symbol", "Name", "Price", "24h%", "Market Cap", "Vol"];
            let widths = [
                Constraint::Length(10),
                Constraint::Length(20),
                Constraint::Length(14),
                Constraint::Length(10),
                Constraint::Length(16),
                Constraint::Length(16),
            ];

            let rows: Vec<Vec<String>> = self
                .crypto
                .iter()
                .map(|c| {
                    vec![
                        c.symbol.clone(),
                        c.name.clone(),
                        format!("${:.2}", c.price),
                        format!("{:.2}%", c.change_pct),
                        format!("${:.0}", c.market_cap),
                        format!("${:.0}", c.volume),
                    ]
                })
                .collect();

            let table = Table::new(
                rows.iter().map(|r| {
                    let cells: Vec<_> = r
                        .iter()
                        .enumerate()
                        .map(|(i, c)| {
                            let color = if i == 3 {
                                let v: f64 = c.trim_end_matches('%').parse().unwrap_or(0.0);
                                if v >= 0.0 {
                                    Color::Green
                                } else {
                                    Color::Red
                                }
                            } else {
                                Color::Green
                            };
                            ratatui::widgets::Cell::new(Span::styled(c, Style::default().fg(color)))
                        })
                        .collect();
                    ratatui::widgets::Row::new(cells)
                }),
                widths,
            )
            .header(
                ratatui::widgets::Row::new(
                    headers.iter().map(|h| ratatui::widgets::Cell::new(Span::styled(*h, header_style))),
                )
                .height(1),
            )
            .block(Block::default().borders(Borders::NONE))
            .row_highlight_style(Style::default().bg(Color::Rgb(0x1A, 0x3A, 0x1A)));

            f.render_stateful_widget(table, inner, &mut self.state);
        }

        let footer = Paragraph::new(
            " [1] Stocks  [2] Crypto  Enter:Select  /:Search  q:Quit ",
        )
        .style(Style::default().fg(Color::Rgb(0x55, 0x55, 0x55)));
        f.render_widget(footer, chunks[0]);

        f.render_widget(block, area);
    }

    fn handle_key(&mut self, key: crossterm::event::KeyEvent) -> Option<AppAction> {
        match key.code {
            crossterm::event::KeyCode::Char('1') => {
                self.tab = 0;
                None
            }
            crossterm::event::KeyCode::Char('2') => {
                self.tab = 1;
                None
            }
            crossterm::event::KeyCode::Char('/') | crossterm::event::KeyCode::Char('s') => {
                Some(AppAction::Search)
            }
            crossterm::event::KeyCode::Enter => {
                let idx = self.state.selected().unwrap_or(0);
                let sym = if self.tab == 0 {
                    self.stocks.get(idx).map(|s| s.symbol.clone())
                } else {
                    self.crypto.get(idx).map(|c| c.symbol.clone())
                };
                sym.map(|s| AppAction::SwitchScreen(ScreenId::StockDetail(s)))
            }
            crossterm::event::KeyCode::Up => {
                let n = if self.tab == 0 { self.stocks.len() } else { self.crypto.len() };
                let i = self.state.selected().unwrap_or(0);
                self.state.select(Some(i.saturating_sub(1).min(n.saturating_sub(1))));
                None
            }
            crossterm::event::KeyCode::Down => {
                let n = if self.tab == 0 { self.stocks.len() } else { self.crypto.len() };
                let i = self.state.selected().unwrap_or(0);
                self.state.select(Some((i + 1).min(n.saturating_sub(1))));
                None
            }
            crossterm::event::KeyCode::Char('q') => Some(AppAction::Quit),
            _ => None,
        }
    }
}
