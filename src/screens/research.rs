use crate::db::ResearchPaper;
use crate::screens::{AppAction, Screen};
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListState, Paragraph};
use ratatui::Frame;

pub struct Research {
    papers: Vec<ResearchPaper>,
    state: ListState,
    loading: bool,
}

impl Research {
    pub fn new() -> Self {
        Research {
            papers: Vec::new(),
            state: ListState::default(),
            loading: true,
        }
    }

    pub fn set_papers(&mut self, papers: Vec<ResearchPaper>) {
        self.papers = papers;
        self.loading = false;
    }
}

impl Screen for Research {
    fn draw(&mut self, f: &mut Frame, area: Rect) {
        let title = if self.loading {
            " RESEARCH [loading...] "
        } else {
            " RESEARCH "
        };
        let block = Block::default()
            .title(title)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(0xFF, 0xB0, 0x00)))
            .title_style(Style::default().add_modifier(Modifier::BOLD));

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Min(0), Constraint::Length(1)])
            .split(area);

        let items: Vec<_> = self
            .papers
            .iter()
            .map(|p| {
                let line = format!("{} — {}", p.title, p.authors);
                ratatui::widgets::ListItem::new(Line::from(Span::styled(
                    line,
                    Style::default().fg(Color::Green),
                )))
            })
            .collect();

        let list = List::new(items)
            .block(Block::default().borders(Borders::NONE))
            .highlight_style(Style::default().bg(Color::Rgb(0x1A, 0x3A, 0x1A)));

        f.render_stateful_widget(list, chunks[0], &mut self.state);

        let footer = Paragraph::new(" q:Back ")
            .style(Style::default().fg(Color::Rgb(0x55, 0x55, 0x55)));
        f.render_widget(footer, chunks[1]);

        f.render_widget(block, area);
    }

    fn handle_key(&mut self, key: crossterm::event::KeyEvent) -> Option<AppAction> {
        match key.code {
            crossterm::event::KeyCode::Char('q') => Some(AppAction::Back),
            crossterm::event::KeyCode::Up => {
                let i = self.state.selected().unwrap_or(0);
                self.state.select(Some(i.saturating_sub(1)));
                None
            }
            crossterm::event::KeyCode::Down => {
                let i = self.state.selected().unwrap_or(0);
                self.state.select(Some((i + 1).min(self.papers.len().saturating_sub(1))));
                None
            }
            _ => None,
        }
    }
}
