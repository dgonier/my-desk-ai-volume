"""
Article scraping and storage for tech news, LLM research, etc.

Sources:
- Hacker News (news.ycombinator.com)
- Arxiv (for AI/ML papers)
- Tech blogs (via RSS or web scraping)
"""

import sys
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx
from bs4 import BeautifulSoup

# Add packages to path
sys.path.insert(0, '/packages')

from cognitive import get_graph, NodeType, RelationType
from cognitive.models import ArticleNode


def scrape_articles(
    topic: str,
    sources: Optional[List[str]] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Scrape articles about a topic from various sources.

    Args:
        topic: Search topic (e.g., "LLM", "machine learning", "AI agents")
        sources: List of sources to scrape (default: ["hackernews", "arxiv"])
        limit: Maximum articles per source

    Returns:
        List of article dicts with title, url, summary, source, etc.
    """
    sources = sources or ["hackernews"]
    articles = []

    for source in sources:
        if source == "hackernews":
            articles.extend(_scrape_hackernews(topic, limit))
        elif source == "arxiv":
            articles.extend(_scrape_arxiv(topic, limit))
        # Add more sources as needed

    return articles


def _scrape_hackernews(topic: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Scrape Hacker News for articles matching a topic."""
    articles = []

    try:
        # Use Algolia HN Search API
        url = f"https://hn.algolia.com/api/v1/search"
        params = {
            "query": topic,
            "tags": "story",
            "hitsPerPage": limit
        }

        response = httpx.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        for hit in data.get("hits", []):
            article = {
                "title": hit.get("title", ""),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "source": "Hacker News",
                "author": hit.get("author"),
                "published_date": hit.get("created_at"),
                "points": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
                "hn_id": hit.get("objectID"),
            }
            articles.append(article)

    except Exception as e:
        print(f"Error scraping Hacker News: {e}")

    return articles


def _scrape_arxiv(topic: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Scrape arXiv for papers matching a topic."""
    articles = []

    try:
        # Use arXiv API
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{topic}",
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        response = httpx.get(url, params=params, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml-xml")

        for entry in soup.find_all("entry"):
            title = entry.find("title")
            summary = entry.find("summary")
            published = entry.find("published")
            authors = entry.find_all("author")
            link = entry.find("id")

            article = {
                "title": title.text.strip() if title else "",
                "url": link.text.strip() if link else "",
                "source": "arXiv",
                "summary": summary.text.strip() if summary else "",
                "author": ", ".join([a.find("name").text for a in authors[:3]]) if authors else None,
                "published_date": published.text if published else None,
            }
            articles.append(article)

    except Exception as e:
        print(f"Error scraping arXiv: {e}")

    return articles


def save_article(
    title: str,
    url: str,
    source: str,
    summary: Optional[str] = None,
    author: Optional[str] = None,
    published_date: Optional[str] = None,
    topics: Optional[List[str]] = None,
    **extra_props
) -> str:
    """
    Save an article to the cognitive graph.

    Args:
        title: Article title
        url: Article URL
        source: Source name (e.g., "Hacker News", "arXiv")
        summary: Article summary/abstract
        author: Author name
        published_date: Publication date string
        topics: List of topic names to link
        **extra_props: Additional properties

    Returns:
        Neo4j element ID of the created article node
    """
    graph = get_graph()

    # Create article node
    article = ArticleNode.create(
        title=title,
        url=url,
        source=source,
        summary=summary,
        author=author,
        published_date=datetime.fromisoformat(published_date) if published_date else None,
        **extra_props
    )

    article_id = graph.create_node(article)

    # Link to topics
    if topics:
        graph.link_to_topics(article_id, topics)

    # Link user to article (RESEARCHED relationship)
    user = graph.get_user()
    if user:
        graph.create_relationship(
            user["id"],
            article_id,
            RelationType.RESEARCHED
        )

    return article_id


def save_articles_batch(articles: List[Dict[str, Any]], topic: str) -> int:
    """
    Save multiple articles to the graph.

    Args:
        articles: List of article dicts from scrape_articles
        topic: Topic to link all articles to

    Returns:
        Number of articles saved
    """
    count = 0
    for article in articles:
        try:
            save_article(
                title=article.get("title", "Untitled"),
                url=article.get("url", ""),
                source=article.get("source", "Unknown"),
                summary=article.get("summary"),
                author=article.get("author"),
                published_date=article.get("published_date"),
                topics=[topic],
                **{k: v for k, v in article.items()
                   if k not in ["title", "url", "source", "summary", "author", "published_date"]}
            )
            count += 1
        except Exception as e:
            print(f"Error saving article: {e}")
    return count


def get_articles(
    topic: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get articles from the cognitive graph.

    Args:
        topic: Filter by topic name
        source: Filter by source
        limit: Maximum articles to return

    Returns:
        List of article dicts
    """
    graph = get_graph()

    if topic:
        # Get articles linked to a topic
        topic_node = graph.find_node_by_name(NodeType.TOPIC, topic)
        if topic_node:
            return graph.get_related_nodes(
                topic_node["id"],
                rel_type=RelationType.ABOUT_TOPIC,
                direction="incoming",
                target_type=NodeType.ARTICLE,
                limit=limit
            )
        return []

    filters = {}
    if source:
        filters["source"] = source

    return graph.find_nodes(NodeType.ARTICLE, filters, limit)


def search_articles(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search articles by title.

    Args:
        query: Search text
        limit: Maximum results

    Returns:
        List of matching articles
    """
    graph = get_graph()
    return graph.search_nodes(NodeType.ARTICLE, query, "name", limit)


def scrape_and_save(
    topic: str,
    sources: Optional[List[str]] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Convenience function to scrape articles and save them in one call.

    Args:
        topic: Topic to search for
        sources: Sources to scrape
        limit: Max articles per source

    Returns:
        Dict with count and articles saved
    """
    articles = scrape_articles(topic, sources, limit)
    saved_count = save_articles_batch(articles, topic)

    return {
        "topic": topic,
        "scraped": len(articles),
        "saved": saved_count,
        "articles": articles[:10]  # Return first 10 for preview
    }
