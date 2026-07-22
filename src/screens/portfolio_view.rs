use crate::db::{Database, Portfolio, Position, Trade};
use crate::screens::{AppAction, Screen};
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Paragraph, Table, TableState};
use ratatui::Frame;
use std::sync::Arc;

pub struct PortfolioView {
    db: Arc<Database>,
    portfolio_id: i64,
    portfolio: Option<Portfolio>,
    positions: Vec<Position>,
    trades: Vec<Trade>,
    tab: usize,
    pos_state: TableState,
    trade_state: TableState,
}

impl PortfolioView {
    pub fn new(db: Arc<Database>, portfolio_id: i64) -> Self {
        let portfolio = db.get_portfolio(portfolio_id);
        let positions = db.get_positions(portfolio_id);
        let trades = db.get_trades(portfolio_id);
        PortfolioView {
            db,
            portfolio_id,
            portfolio,
            positions,
            trades,
            tab: 0,
            pos_state: TableState::default(),
            trade_state: TableState::default(),
        }
    }

    pub fn refresh(&mut self) {
        self.portfolio = self.db.get_portfolio(self.portfolio_id);
        self.positions = self.db.get_positions(self.portfolio_id);
        self.trades = self.db.get_trades(self.portfolio_id);
    }
}

impl Screen for PortfolioView {
    fn draw(&mut self, f: &mut Frame, area: Rect) {
        let block = Block::default()
            .title(" PORTFOLIO ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(0xFF, 0xB0, 0x00)))
            .title_style(Style::default().add_modifier(Modifier::BOLD));

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4),
                Constraint::Length(3),
                Constraint::Min(0),
            ])
            .split(area);

        if let Some(ref p) = self.portfolio {
            let pos_value: f64 = self.positions.iter().map(|p| p.current_value).sum();
            let total = p.cash_balance + pos_value;
            let summary = Paragraph::new(vec![Line::from(vec![
                Span::styled("Cash: ", Style::default().fg(Color::Rgb(0x80, 0x80, 0x80))),
                Span::styled(
                    format!("${:.2}", p.cash_balance),
                    Style::default().fg(Color::Green),
                ),
                Span::raw("  "),
                Span::styled(
                    "Positions: ",
                    Style::default().fg(Color::Rgb(0x80, 0x80, 0x80)),
                ),
                Span::styled(
                    format!("${:.2}", pos_value),
                    Style::default().fg(Color::Green),
                ),
                Span::raw("  "),
                Span::styled("Total: ", Style::default().fg(Color::Rgb(0x80, 0x80, 0x80))),
                Span::styled(
                    format!("${:.2}", total),
                    Style::default()
                        .fg(Color::Green)
                        .add_modifier(Modifier::BOLD),
                ),
            ])])
            .block(Block::default().borders(Borders::NONE));
            f.render_widget(summary, chunks[0]);
        }

        let tabs = Paragraph::new(Line::from(vec![
            Span::styled(
                " [1] Holdings ",
                Style::default().fg(if self.tab == 0 {
                    Color::Rgb(0xFF, 0xB0, 0x00)
                } else {
                    Color::Green
                }),
            ),
            Span::raw(" | "),
            Span::styled(
                " [2] Trade History ",
                Style::default().fg(if self.tab == 1 {
                    Color::Rgb(0xFF, 0xB0, 0x00)
                } else {
                    Color::Green
                }),
            ),
        ]));
        f.render_widget(tabs, chunks[1]);

        let inner = chunks[2];
        let hdr = Style::default()
            .fg(Color::Rgb(0xFF, 0xB0, 0x00))
            .add_modifier(Modifier::BOLD);

        if self.tab == 0 {
            let headers = ["Symbol", "Qty", "Avg Cost", "Value", "P/L"];
            let widths = [
                Constraint::Length(10),
                Constraint::Length(12),
                Constraint::Length(12),
                Constraint::Length(14),
                Constraint::Length(14),
            ];

            let rows: Vec<Vec<String>> = self
                .positions
                .iter()
                .map(|p| {
                    let pl = p.current_value - (p.quantity * p.avg_cost);
                    vec![
                        p.symbol.clone(),
                        format!("{:.4}", p.quantity),
                        format!("${:.2}", p.avg_cost),
                        format!("${:.2}", p.current_value),
                        format!("${:.2}", pl),
                    ]
                })
                .collect();

            let table = Table::new(
                rows.iter().map(|r| {
                    ratatui::widgets::Row::new(r.iter().map(|c| {
                        ratatui::widgets::Cell::new(Span::styled(
                            c,
                            Style::default().fg(Color::Green),
                        ))
                    }))
                }),
                widths,
            )
            .header(ratatui::widgets::Row::new(
                headers
                    .iter()
                    .map(|h| ratatui::widgets::Cell::new(Span::styled(*h, hdr))),
            ))
            .block(Block::default().borders(Borders::NONE))
            .row_highlight_style(Style::default().bg(Color::Rgb(0x1A, 0x3A, 0x1A)));

            f.render_stateful_widget(table, inner, &mut self.pos_state);
        } else {
            let headers = ["Symbol", "Side", "Qty", "Price", "Total", "Time"];
            let widths = [
                Constraint::Length(10),
                Constraint::Length(8),
                Constraint::Length(10),
                Constraint::Length(12),
                Constraint::Length(14),
                Constraint::Length(20),
            ];

            let rows: Vec<Vec<String>> = self
                .trades
                .iter()
                .map(|t| {
                    vec![
                        t.symbol.clone(),
                        t.side.clone(),
                        format!("{:.4}", t.quantity),
                        format!("${:.2}", t.price),
                        format!("${:.2}", t.quantity * t.price),
                        t.timestamp.clone(),
                    ]
                })
                .collect();

            let table = Table::new(
                rows.iter().map(|r| {
                    ratatui::widgets::Row::new(r.iter().map(|c| {
                        ratatui::widgets::Cell::new(Span::styled(
                            c,
                            Style::default().fg(Color::Green),
                        ))
                    }))
                }),
                widths,
            )
            .header(ratatui::widgets::Row::new(
                headers
                    .iter()
                    .map(|h| ratatui::widgets::Cell::new(Span::styled(*h, hdr))),
            ))
            .block(Block::default().borders(Borders::NONE))
            .row_highlight_style(Style::default().bg(Color::Rgb(0x1A, 0x3A, 0x1A)));

            f.render_stateful_widget(table, inner, &mut self.trade_state);
        }

        let footer = Paragraph::new(" 1:Holdings  2:History  q:Back ")
            .style(Style::default().fg(Color::Rgb(0x55, 0x55, 0x55)));
        f.render_widget(
            footer,
            Rect::new(area.x, area.y + area.height - 1, area.width, 1),
        );

        f.render_widget(block, area);
    }

    fn handle_key(&mut self, key: crossterm::event::KeyEvent) -> Option<AppAction> {
        match key.code {
            crossterm::event::KeyCode::Char('1') => self.tab = 0,
            crossterm::event::KeyCode::Char('2') => self.tab = 1,
            crossterm::event::KeyCode::Char('q') => return Some(AppAction::Back),
            _ => {}
        }
        None
    }
}
