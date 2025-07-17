import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.core.database import vector_store
from app.core.embeddings import embedding_service
from app.models.models import NewsArticle
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)


class RAGChain:
    """Retrieval-Augmented Generation chain for crypto news Q&A with chat history"""

    def __init__(self):
        self.llm = ChatOpenAI(model=settings.llm_model, temperature=0.1, streaming=True)
        self._setup_prompts()

    def _setup_prompts(self):
        """Setup the prompts for history-aware retrieval"""

        # Prompt for generating a search query from conversation history
        self.history_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a helpful AI assistant that helps find relevant crypto news articles.\n"
                        "Given a conversation history and a new question, generate a search query that would help find "
                        "the most relevant recent crypto news articles.\n"
                        "\n"
                        "Focus on the key topics, entities, and concepts mentioned in the conversation.\n"
                        "Return only the search query, nothing else.\n"
                        "\n"
                        "IMPORTANT: Only refuse to answer if the question is clearly offensive, abusive, or requests "
                        "illegal or harmful information.\n"
                        "Questions about eligibility, participation, or regulations are valid and should be answered "
                        "factually if possible.\n"
                        "For example, if asked 'Who is not allowed to participate in the upcoming ICO?', generate a "
                        "search query about ICO participation rules.\n"
                    ),
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

        # Prompt for answering with retrieved context
        self.answer_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a helpful AI assistant that answers questions about cryptocurrency news and events.\n"
                        "You have access to recent crypto news articles retrieved from our database.\n"
                        "Use these articles as your primary source of information to answer the user's question.\n"
                        "The chat history is provided only for conversational context, not as a source of news facts.\n"
                        "If the articles contain relevant information, provide a detailed answer based on them.\n"
                        "If the articles don't contain specific information about the question, acknowledge this, but "
                        "provide any related insights from the available articles.\n"
                        "Do not make up information that is not present in the articles.\n"
                        "Keep the answer concise and informative.\n"
                        "\n"
                        "IMPORTANT SAFETY GUIDELINES:\n"
                        "- Do not provide advice on illegal activities, scams, or fraudulent schemes\n"
                        "- Do not promote harmful financial practices or risky investments\n"
                        "- Do not generate content that could be considered offensive, discriminatory, or inappropriate\n"
                        "- If asked about potentially harmful topics, politely redirect to legitimate crypto news and "
                        "information\n"
                        "- Focus on factual, educational content about cryptocurrency markets and technology\n"
                        "\n"
                        "Retrieved News Articles:\n"
                        "{context}"
                    ),
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

    def _create_retriever(self):
        """Create a retriever from the vector store"""

        async def retrieve_docs(question: str) -> List[NewsArticle]:
            # get embedding for the question
            query_embedding = await embedding_service.get_embedding(question)

            # search for similar articles
            articles = await vector_store.search_similar(
                query_embedding=query_embedding, limit=settings.max_retrieval_results
            )

            return articles

        return retrieve_docs

    def _convert_to_messages(self, chat_history: List[Dict[str, str]]) -> List:
        """Convert chat history to LangChain messages"""
        messages = []
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
        return messages

    def _format_context(self, articles: List[NewsArticle]) -> str:
        """Format articles into context string"""
        if not articles:
            return (
                "No recent crypto news articles available in the database. "
                "The system is still ingesting news articles. Please try again in a few minutes."
            )

        context_parts = []
        for i, article in enumerate(articles, 1):
            context_parts.append(f"{i}. {article.title}")
            if article.summary:
                context_parts.append(f"   Summary: {article.summary}")
            context_parts.append(f"   Source: {article.source}")
            context_parts.append(f"   Published: {article.published_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            context_parts.append("")

        return "\n".join(context_parts)

    async def answer_question(self, question: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Answer a question using the RAG chain with conversation history"""
        try:
            logger.info(f"RAG: Processing question: '{question[:50]}...'")

            # Convert chat history to LangChain messages
            messages = self._convert_to_messages(chat_history or [])
            if messages:
                logger.info(f"RAG: Using {len(messages)} previous messages for context")

            # step 1: generate better search query using conversation history
            search_query = question
            if messages:
                logger.info("RAG: Generating history-aware search query...")
                history_chain = self.history_prompt | self.llm
                search_query_result = await history_chain.ainvoke({"question": question, "chat_history": messages})
                # extract content from aimessage
                if hasattr(search_query_result, "content"):
                    search_query = search_query_result.content
                else:
                    search_query = str(search_query_result)

                # check for moderation response
                if "I cannot help with that request" in search_query:
                    logger.warning(f"RAG: Moderation triggered for question: '{question[:50]}...'")
                    return {
                        "answer": (
                            "I apologize, but I cannot help with that request. "
                            "Please ask questions related to cryptocurrency news and legitimate market information."
                        ),
                        "sources": [],
                        "question": question,
                    }

                logger.info(f"RAG: Generated search query: '{search_query[:50]}...'")

            # step 2: retrieve relevant articles using enhanced query
            logger.info(f"RAG: Searching for articles with query: '{search_query[:50]}...'")
            articles = await self._create_retriever()(search_query)
            logger.info(f"RAG: Found {len(articles)} relevant articles")

            # deduplicate articles based on url
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    unique_articles.append(article)

            logger.info(f"RAG: Deduplicated to {len(unique_articles)} unique articles")

            # step 3: generate answer using retrieved context and conversation history
            context = self._format_context(unique_articles)
            logger.debug(f"RAG: Context length: {len(context)} characters")

            # create input for answer chain
            answer_chain = self.answer_prompt | self.llm
            chain_input = {"context": context, "chat_history": messages, "question": question}

            # run answer chain
            logger.info("RAG: Generating answer with context and history...")
            result = await answer_chain.ainvoke(chain_input)
            if hasattr(result, "content"):
                answer = result.content
            else:
                answer = str(result)
            logger.info(f"RAG: Generated answer ({len(answer)} characters)")

            return {"answer": answer, "sources": unique_articles, "question": question}

        except Exception as e:
            logger.error(f"Error in RAG chain for question '{question[:50]}...': {e}", exc_info=True)
            raise

    async def get_relevant_articles(self, question: str) -> List[NewsArticle]:
        """Get relevant articles for a question without generating an answer"""
        return await self._create_retriever()(question)


# Global RAG chain instance
rag_chain = RAGChain()
