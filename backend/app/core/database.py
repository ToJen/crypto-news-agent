import logging
from datetime import datetime
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from app.core.config import settings
from app.models.models import NewsArticle

logger = logging.getLogger(__name__)


class VectorStore:
    """Qdrant vector store for crypto news articles"""

    def __init__(self):
        self.client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self.collection_name = settings.qdrant_collection
        # Note: _ensure_collection will be called when needed in async methods

    async def _ensure_collection(self):
        """Ensure the collection exists with proper configuration"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                # Try to determine the correct vector size based on the embedding service
                from app.embeddings import embedding_service

                try:
                    # Test with a small text to get the embedding dimension
                    test_embedding = await embedding_service.get_embedding("test")
                    vector_size = len(test_embedding)
                    logger.info(f"Detected embedding dimension: {vector_size}")
                except Exception as e:
                    logger.warning(f"Could not determine embedding dimension, using default 1536: {e}")
                    vector_size = 1536  # Default to OpenAI dimension

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
                logger.info(f"Created collection: {self.collection_name} with {vector_size} dimensions")
            else:
                logger.info(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise

    async def add_articles(self, articles: List[NewsArticle], embeddings: List[List[float]]):
        """Add articles with their embeddings to the vector store"""
        try:
            await self._ensure_collection()

            points = []
            for article, embedding in zip(articles, embeddings):
                point = PointStruct(
                    id=abs(hash(article.url)) % (2**63),  # Convert to positive unsigned 64-bit integer
                    vector=embedding,
                    payload={
                        "title": article.title,
                        "url": article.url,
                        "source": article.source,
                        "published_at": article.published_at.isoformat(),
                        "content": article.content,
                        "summary": article.summary,
                    },
                )
                points.append(point)

            # Use upsert to handle duplicates
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info(f"Added {len(articles)} articles to vector store")

        except Exception as e:
            logger.error(f"Error adding articles to vector store: {e}")
            raise

    async def add_article(self, article: NewsArticle, embedding: List[float]):
        """Add a single article to the vector store"""
        try:
            await self._ensure_collection()

            point = PointStruct(
                id=abs(hash(article.url)) % (2**63),  # Convert to positive unsigned 64-bit integer
                vector=embedding,
                payload={
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "published_at": article.published_at.isoformat(),
                    "content": article.content,
                    "summary": article.summary,
                },
            )

            self.client.upsert(collection_name=self.collection_name, points=[point])
            logger.debug(f"DB: Stored article '{article.title[:50]}...' from {article.source}")

        except Exception as e:
            logger.error(f"Error adding article '{article.title[:50]}...' to vector store: {e}", exc_info=True)
            raise

    async def article_exists(self, url: str) -> bool:
        """Check if an article with the given URL already exists"""
        try:
            await self._ensure_collection()

            point_id = abs(hash(url)) % (2**63)  # Use same hash calculation as add_article
            result = self.client.retrieve(collection_name=self.collection_name, ids=[point_id], with_payload=True)
            return len(result) > 0
        except Exception as e:
            logger.debug(f"Error checking article existence: {e}")
            return False

    async def search_similar(
        self, query_embedding: List[float], limit: int = 5, filters: Optional[Filter] = None
    ) -> List[NewsArticle]:
        """Search for similar articles"""
        try:
            await self._ensure_collection()

            logger.debug(f"DB: Searching for {limit} similar articles")
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=filters,
                with_payload=True,
            )

            articles = []
            for result in search_result:
                payload = result.payload
                article = NewsArticle(
                    title=payload["title"],
                    url=payload["url"],
                    source=payload["source"],
                    published_at=datetime.fromisoformat(payload["published_at"]),
                    content=payload.get("content"),
                    summary=payload.get("summary"),
                )
                articles.append(article)

            logger.debug(f"DB: Found {len(articles)} similar articles")
            return articles

        except Exception as e:
            logger.error(f"Error searching vector store: {e}", exc_info=True)
            raise

    async def get_recent_articles(self, hours: int = 24) -> List[NewsArticle]:
        """Get articles published in the last N hours"""
        try:
            await self._ensure_collection()

            from datetime import datetime, timedelta

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Create filter for recent articles
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="published_at",
                        match=MatchValue(value=cutoff_time.isoformat(), range={"gte": cutoff_time.isoformat()}),
                    )
                ]
            )

            # Get the vector size from the collection
            collection_info = self.client.get_collection(self.collection_name)
            vector_size = collection_info.config.params.vectors.size

            # Search with filter (using zero vector to get all recent articles)
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=[0.0] * vector_size,  # Dummy vector with correct size
                limit=100,
                query_filter=filter_condition,
                with_payload=True,
            )

            articles = []
            for result in search_result:
                payload = result.payload
                article = NewsArticle(
                    title=payload["title"],
                    url=payload["url"],
                    source=payload["source"],
                    published_at=datetime.fromisoformat(payload["published_at"]),
                    content=payload.get("content"),
                    summary=payload.get("summary"),
                )
                articles.append(article)

            return articles

        except Exception as e:
            logger.error(f"Error getting recent articles: {e}")
            raise

    async def get_article_count(self) -> int:
        """Get total number of articles in the database"""
        try:
            await self._ensure_collection()

            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Error getting article count: {e}")
            return 0


# Global vector store instance
vector_store = VectorStore()
