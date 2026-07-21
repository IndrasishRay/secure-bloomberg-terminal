pub mod arxiv;

use crate::db::ResearchPaper;

pub async fn fetch_papers() -> Vec<ResearchPaper> {
    arxiv::fetch_papers().await.unwrap_or_default()
}
