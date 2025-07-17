import logging
from typing import List

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

load_dotenv()

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI or HuggingFace"""

    def __init__(self):
        self.openai_embeddings = OpenAIEmbeddings(
            model=settings.embedding_model, openai_api_key=settings.openai_api_key
        )

        # Fallback to HuggingFace if needed
        self.hf_embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        self.use_openai = True

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts"""
        try:
            if self.use_openai:
                embeddings = await self.openai_embeddings.aembed_documents(texts)
                logger.info(f"Generated {len(embeddings)} embeddings using OpenAI")
                return embeddings
            else:
                embeddings = self.hf_embeddings.embed_documents(texts)
                logger.info(f"Generated {len(embeddings)} embeddings using HuggingFace")
                return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Fallback to HuggingFace if OpenAI fails
            if self.use_openai:
                logger.info("Falling back to HuggingFace embeddings")
                self.use_openai = False
                return await self.get_embeddings(texts)
            else:
                raise

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        embeddings = await self.get_embeddings([text])
        return embeddings[0]

    def switch_to_huggingface(self):
        """Switch to HuggingFace embeddings (for cost control)"""
        self.use_openai = False
        logger.info("Switched to HuggingFace embeddings")


# Global embedding service instance
embedding_service = EmbeddingService()
