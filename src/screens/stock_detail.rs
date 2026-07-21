use crate::market::{get_stock_quote, StockQuote};
use crate::screens::{AppAction, Screen};
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Gauge, Paragraph, Wrap};
use ratatui::Frame;

pub struct StockDetail {
    pub symbol: String,
    quote: Option<StockQuote>,
    loading: bool,
    buy_amount: String,
    sell_amount: String,
    focus: Focus,
    error: Option<String>,
    message: Option<String>,
}

enum Focus {
    Buy,
    Sell,
    None,
}

impl StockDetail {
    pub fn new(symbol: String) -> Self {
        StockDetail {
            symbol,
            quote: None,
            loading: true,
            buy_amount: String::new(),
            sell_amount: String::new(),
            focus: Focus::None,
            error: None,
            message: None,
        }
    }

    pub async fn refresh(&mut self) {
        self.loading = true;
        self.quote = get_stock_quote(&self.symbol).await.ok();
        self.loading = false;
    }

    pub fn current_price(&self) -> Option<f64> {
        self.quote.as_ref().map(|q| q.price)
    }

    pub fn buy_qty(&self) -> f64 {
        self.buy_amount.parse().unwrap_or(0.0)
    }

    pub fn sell_qty(&self) -> f64 {
        self.sell_amount.parse().unwrap_or(0.0)
    }

    pub fn set_message(&mut self, msg: String) {
        self.message = Some(msg);
    }
}

impl Screen for StockDetail {
    fn draw(&mut self, f: &mut Frame, area: Rect) {
        let title = format!(" {} ", self.symbol);
        let block = Block::default()
            .title(title.as_str())
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(0xFF, 0xB0, 0x00)))
            .title_style(Style::default().add_modifier(Modifier::BOLD));

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(8),
                Constraint::Length(3),
                Constraint::Length(3),
                Constraint::Length(3),
                Constraint::Min(0),
            ])
            .split(area);

        if let Some(ref q) = self.quote {
            let change_color = if q.change >= 0.0 { Color::Green } else { Color::Red };
            let info = Paragraph::new(vec![
                Line::from(vec![
                    Span::styled("Price: ", Style::default().fg(Color::Rgb(0x80, 0x80, 0x80))),
                    Span::styled(
                        format!("${:.2}", q.price),
                        Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                    ),
                    Span::raw("  "),
                    Span::styled(
                        format!("{:.2} ({:.2}%)", q.change, q.change_pct),
                        Style::default().fg(change_color),
                    ),
                ]),
                Line::from(""),
                Line::from(vec![
                    Span::styled("Open: ", Style::default().fg(Color::Rgb(0x80, 0x80, 0x80))),
                    Span::styled(format!("${:.2}", q.open), Style::default().fg(Color::Green)),
                    Span::raw("  "),
                    Span::styled("High: ", Style::default().fg(Color::Rgb(0x80, 0x80, 0x80))),
                    Span::styled(format!("${:.2}", q.high), Style::default().fg(Color::Green)),
                    Span::raw("  "),
                    Span::styled("Low: ", Style::default().fg(Color::Rgb(0x80, 0x80, 0x80))),
                    Span::styled(format!("${:.2}", q.low), Style::default().fg(Color::Green)),
                ]),
                Line::from(vec![
                    Span::styled("Prev Close: ", Style::default().fg(Color::Rgb(0x80, 0x80, 0x80))),
                    Span::styled(format!("${:.2}", q.prev_close), Style::default().fg(Color::Green)),
                    Span::raw("  "),
                    Span::styled("Volume: ", Style::default().fg(Color::Rgb(0x80, 0x80, 0x80))),
                    Span::styled(q.volume.to_string(), Style::default().fg(Color::Green)),
                ]),
            ])
            .block(Block::default().borders(Borders::NONE))
            .wrap(Wrap { trim: false });

            f.render_widget(info, chunks[0]);

            if q.prev_close > 0.0 {
                let pct = ((q.price / q.prev_close) * 100.0).min(100.0) as f64;
                let gauge = Gauge::default()
                    .block(Block::default().title("Day Range").borders(Borders::ALL))
                    .gauge_style(Style::default().fg(change_color))
                    .percent(pct as u16)
                    .label(format!("${:.2} / ${:.2}", q.low, q.high));
                f.render_widget(gauge, chunks[1]);
            }
        } else if self.loading {
            let loading = Paragraph::new("Loading...")
                .style(Style::default().fg(Color::Rgb(0x80, 0x80, 0x80)))
                .block(Block::default().borders(Borders::NONE));
            f.render_widget(loading, chunks[0]);
        }

        if let Some(ref err) = self.error {
            let err_w = Paragraph::new(err.as_str()).style(Style::default().fg(Color::Red));
            f.render_widget(err_w, chunks[4]);
        }
        if let Some(ref msg) = self.message {
            let msg_w =
                Paragraph::new(msg.as_str()).style(Style::default().fg(Color::Rgb(0xFF, 0xB0, 0x00)));
            f.render_widget(msg_w, chunks[4]);
        }

        let buy_style = if matches!(self.focus, Focus::Buy) {
            Style::default().fg(Color::Rgb(0xFF, 0xB0, 0x00))
        } else {
            Style::default().fg(Color::Green)
        };
        let sell_style = if matches!(self.focus, Focus::Sell) {
            Style::default().fg(Color::Rgb(0xFF, 0xB0, 0x00))
        } else {
            Style::default().fg(Color::Green)
        };

        let buy_block = Block::default()
            .title(" Buy ")
            .borders(Borders::ALL)
            .border_style(buy_style);
        let buy_p = Paragraph::new(if self.buy_amount.is_empty() { "Enter qty..." } else { &self.buy_amount })
            .block(buy_block);
        f.render_widget(buy_p, chunks[2]);

        let sell_block = Block::default()
            .title(" Sell ")
            .borders(Borders::ALL)
            .border_style(sell_style);
        let sell_p = Paragraph::new(if self.sell_amount.is_empty() { "Enter qty..." } else { &self.sell_amount })
            .block(sell_block);
        f.render_widget(sell_p, chunks[3]);

        let footer = Paragraph::new(" Tab:Toggle buy/sell  Enter:Execute  q:Back ")
            .style(Style::default().fg(Color::Rgb(0x55, 0x55, 0x55)));
        f.render_widget(footer, Rect::new(area.x, area.y + area.height - 1, area.width, 1));

        f.render_widget(block, area);
    }

    fn handle_key(&mut self, key: crossterm::event::KeyEvent) -> Option<AppAction> {
        match key.code {
            crossterm::event::KeyCode::Char('q') => Some(AppAction::Back),
            crossterm::event::KeyCode::Char('/') | crossterm::event::KeyCode::Char('s') => {
                Some(AppAction::Search)
            }
            crossterm::event::KeyCode::Tab => {
                self.focus = match self.focus {
                    Focus::None => Focus::Buy,
                    Focus::Buy => Focus::Sell,
                    Focus::Sell => Focus::Buy,
                };
                None
            }
            crossterm::event::KeyCode::Char(c) if c.is_ascii_digit() || c == '.' => {
                match self.focus {
                    Focus::Buy => {
                        self.buy_amount.push(c);
                    }
                    Focus::Sell => {
                        self.sell_amount.push(c);
                    }
                    Focus::None => {}
                }
                None
            }
            crossterm::event::KeyCode::Backspace => {
                match self.focus {
                    Focus::Buy => {
                        self.buy_amount.pop();
                    }
                    Focus::Sell => {
                        self.sell_amount.pop();
                    }
                    Focus::None => {}
                }
                None
            }
            crossterm::event::KeyCode::Enter => {
                match self.focus {
                    Focus::Buy => {
                        let qty = self.buy_amount.parse::<f64>().unwrap_or(0.0);
                        if qty > 0.0 {
                            return Some(AppAction::Buy(self.symbol.clone()));
                        }
                    }
                    Focus::Sell => {
                        let qty = self.sell_amount.parse::<f64>().unwrap_or(0.0);
                        if qty > 0.0 {
                            return Some(AppAction::Sell(self.symbol.clone()));
                        }
                    }
                    Focus::None => {}
                }
                None
            }
            _ => None,
        }
    }
}
