import asyncio
import logging
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import List

import feedparser
from newsapi import NewsApiClient

from app.core.config import settings
from app.core.database import vector_store
from app.core.embeddings import embedding_service
from app.models.models import NewsArticle

logger = logging.getLogger(__name__)


class NewsIngestionService:
    """Service for ingesting crypto news from NewsAPI and RSS feeds"""

    def __init__(self):
        self.api_key = settings.news_api_key
        self.fetch_interval = 120  # 2min updates
        self.initial_fetch_hours = 24  # get last 24h on startup
        self.ongoing_fetch_hours = 2  # look back 2h for ongoing updates
        # only essential ones
        self.crypto_keywords = ["crypto", "web3", "blockchain", "cryptocurrency", "bitcoin"]
        self.newsapi = NewsApiClient(api_key=self.api_key)
        self.last_fetch_time = None
        self.total_articles_processed = 0
        self.fetch_cycles = 0

        # rss feeds as backup
        self.rss_feeds = ["https://www.dlnews.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]

    async def start_ingestion(self):
        logger.info("Starting real-time crypto news ingestion service")
        logger.info(f"Configuration: {self.fetch_interval}s intervals, {len(self.crypto_keywords)} keywords")

        # initial fetch to populate db with recent articles
        logger.info(f"Performing initial fetch for last {self.initial_fetch_hours} hours...")
        await self._fetch_news(use_initial_fetch=True)

        # start continuous real-time ingestion
        logger.info(f"Starting continuous ingestion every {self.fetch_interval} seconds...")
        while True:
            try:
                await asyncio.sleep(self.fetch_interval)
                self.fetch_cycles += 1
                logger.info(f"Fetch cycle #{self.fetch_cycles} starting...")
                await self._fetch_news(use_initial_fetch=False)
                logger.info(f"Fetch cycle #{self.fetch_cycles} completed, next fetch in {self.fetch_interval}s")
            except Exception as e:
                logger.error(f"Error in news ingestion cycle #{self.fetch_cycles}: {e}", exc_info=True)
                await asyncio.sleep(30)  # shorter retry interval on error

    async def _fetch_news(self, use_initial_fetch: bool = False):
        """Fetch news from both NewsAPI and RSS feeds"""
        try:
            # try newsapi first
            newsapi_articles = await self._fetch_newsapi(use_initial_fetch)

            # always fetch from rss as backup
            rss_articles = await self._fetch_rss_feeds()

            # combine and process all articles
            all_articles = newsapi_articles + rss_articles
            logger.info(f"Total articles fetched: {len(newsapi_articles)} from NewsAPI, {len(rss_articles)} from RSS")

            processed_count = 0
            for article_data in all_articles:
                if await self._process_article(article_data):
                    processed_count += 1

            self.total_articles_processed += processed_count

            if processed_count > 0:
                logger.info(
                    f"Successfully processed {processed_count} new articles (total: {self.total_articles_processed})"
                )
            else:
                logger.debug("No new articles to process")

        except Exception as e:
            logger.error(f"Error fetching news: {e}")

    async def _fetch_newsapi(self, use_initial_fetch: bool = False) -> List[dict]:
        """Fetch news from NewsAPI"""
        try:
            now = datetime.utcnow()

            # use different time windows for initial vs ongoing fetches
            if use_initial_fetch:
                since = now - timedelta(hours=self.initial_fetch_hours)
                logger.info(f"Initial fetch: looking back {self.initial_fetch_hours} hours")
            else:
                since = now - timedelta(hours=self.ongoing_fetch_hours)
                logger.debug(f"Ongoing fetch: looking back {self.ongoing_fetch_hours} hours")

            # use single query with essential crypto terms
            query = " OR ".join(self.crypto_keywords)

            # newsapi sdk is sync, so run in thread
            def fetch():
                return self.newsapi.get_everything(
                    q=query,
                    language="en",
                    sort_by="publishedAt",
                    from_param=since.strftime("%Y-%m-%d"),
                    to=now.strftime("%Y-%m-%d"),
                    page_size=100 if use_initial_fetch else 50,
                )

            data = await asyncio.to_thread(fetch)
            articles = data.get("articles", [])

            if use_initial_fetch:
                logger.info(f"Initial fetch: Retrieved {len(articles)} articles from NewsAPI")
            else:
                logger.debug(f"Ongoing fetch: Retrieved {len(articles)} articles from NewsAPI")

            return articles

        except Exception as e:
            logger.warning(f"NewsAPI fetch failed (likely rate limited): {e}")
            return []

    async def _fetch_rss_feeds(self) -> List[dict]:
        """Fetch news from RSS feeds"""
        all_articles = []

        for feed_url in self.rss_feeds:
            try:
                logger.debug(f"Fetching RSS feed: {feed_url}")

                # feedparser is sync, so run in thread
                def fetch_rss():
                    return feedparser.parse(feed_url)

                feed = await asyncio.to_thread(fetch_rss)

                if feed.bozo:
                    logger.warning(f"RSS feed parsing error for {feed_url}: {feed.bozo_exception}")
                    continue

                for entry in feed.entries:
                    published_at = datetime.utcnow()
                    if entry.get("published"):
                        try:
                            published_at = parsedate_to_datetime(entry.get("published"))
                        except Exception as e:
                            logger.warning(f"Could not parse RSS date '{entry.get('published')}': {e}")

                    article = {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "source": {"name": feed.feed.get("title", "RSS Feed")},
                        "content": entry.get("summary", ""),
                        "description": entry.get("summary", ""),
                        "publishedAt": published_at.isoformat(),
                    }
                    all_articles.append(article)

                logger.debug(f"Retrieved {len(feed.entries)} articles from {feed_url}")

            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_url}: {e}")
                continue

        logger.info(f"RSS fetch: Retrieved {len(all_articles)} total articles from {len(self.rss_feeds)} feeds")
        return all_articles

    async def _process_article(self, article_data: dict) -> bool:
        try:
            title = article_data.get("title", "").strip()
            url = article_data.get("url", "").strip()
            source = article_data.get("source", {}).get("name", "Unknown")
            content = article_data.get("content", "")
            description = article_data.get("description", "")
            published_str = article_data.get("publishedAt", "")
            if published_str:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            else:
                published_at = datetime.utcnow()
            if not title or not url:
                return False
            article = NewsArticle(
                title=title, url=url, source=source, published_at=published_at, content=content, summary=description
            )
            if await vector_store.article_exists(url):
                logger.debug(f"Article already exists, skipping: {title[:50]}...")
                return False
            text_to_embed = f"{title}. {description}. {content}"
            embedding = await embedding_service.get_embedding(text_to_embed)
            await vector_store.add_article(article, embedding)
            logger.debug(f"Stored article: {title[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return False

    async def get_latest_articles_from_db(self, limit: int = 10) -> List[NewsArticle]:
        """Get the latest articles from the database (not from NewsAPI)"""
        try:
            return await vector_store.get_recent_articles(hours=24)
        except Exception as e:
            logger.error(f"Error getting latest articles from database: {e}")
            return []

    async def get_ingestion_stats(self) -> dict:
        """Get ingestion service statistics"""
        try:
            article_count = await vector_store.get_article_count()
            return {
                "total_articles": article_count,
                "total_processed": self.total_articles_processed,
                "fetch_cycles": self.fetch_cycles,
                "fetch_interval_seconds": self.fetch_interval,
                "last_fetch_time": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
                "keywords_count": len(self.crypto_keywords),
                "keywords": self.crypto_keywords,
                "rss_feeds": self.rss_feeds,
            }
        except Exception as e:
            logger.error(f"Error getting ingestion stats: {e}")
            return {"error": str(e)}


news_service = NewsIngestionService()
