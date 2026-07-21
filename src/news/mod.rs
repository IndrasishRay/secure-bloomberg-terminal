pub mod finnhub;
pub mod rss;

use crate::db::NewsArticle;

pub async fn fetch_news() -> Vec<NewsArticle> {
    let mut articles = Vec::new();

    if let Ok(items) = rss::fetch_rss().await {
        articles.extend(items);
    }

    articles.sort_by(|a, b| b.published_at.cmp(&a.published_at));
    articles.truncate(50);
    articles
}
