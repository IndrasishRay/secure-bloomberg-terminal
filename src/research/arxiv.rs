use crate::db::ResearchPaper;
use anyhow::Result;
use quick_xml::de::from_str;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Feed {
    #[serde(rename = "entry")]
    entries: Vec<Entry>,
}

#[derive(Debug, Deserialize)]
struct Entry {
    title: String,
    authors: Vec<Author>,
    summary: String,
    id: String,
    published: String,
}

#[derive(Debug, Deserialize)]
struct Author {
    name: String,
}

pub async fn fetch_papers() -> Result<Vec<ResearchPaper>> {
    let url = "https://export.arxiv.org/api/query?search_query=cat:q-fin&sortBy=submittedDate&sortOrder=descending&max_results=20";
    let resp = reqwest::get(url).await?;
    let body = resp.text().await?;

    let feed: Feed = from_str(&body)?;
    let papers = feed
        .entries
        .into_iter()
        .map(|e| {
            let authors: Vec<String> = e.authors.into_iter().map(|a| a.name).collect();
            ResearchPaper {
                id: 0,
                title: e.title.trim().to_string(),
                authors: authors.join("; "),
                abstract_: e.summary.trim().to_string(),
                url: e.id,
                published_at: Some(e.published),
            }
        })
        .collect();

    Ok(papers)
}
