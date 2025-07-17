# Crypto News Agent Backend

FastAPI backend for real-time crypto news Q&A system. Ingests news from multiple sources, stores articles with embeddings in Qdrant, and uses LangChain RAG to answer user questions with streaming responses.

## Features

- **Multi-source News Ingestion**: NewsAPI + RSS feeds (CoinDesk, Cointelegraph)
- **Real-time Processing**: Fetches news every 2 minutes
- **Semantic Search**: OpenAI embeddings for accurate article retrieval
- **RAG Chain**: LangChain with conversation history and context awareness
- **Streaming API**: Server-Sent Events for word-by-word responses
- **Content Moderation**: Basic filtering for inappropriate requests
- **Smart Deduplication**: Prevents duplicate articles

## API Endpoints

### POST `/api/v1/ask`
Ask questions about crypto news with streaming response.

**Request Body:**
```json
{
  "question": "What's happening with Bitcoin today?",
  "session_id": "optional-session-id",
  "chat_history": [
    {
      "role": "user",
      "content": "Previous question",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ]
}
```

**Response:** Server-Sent Events stream with:
- `answer_chunk` events: Word-by-word response
- `answer_complete` event: Final response with sources

## Installation

1. **Install dependencies**:
   ```bash
   cd backend
   poetry install
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start Qdrant** (if not running):
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

4. **Run the server**:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

5. **Access the services**:
   - Backend API: http://localhost:8000
   - Qdrant Dashboard: http://localhost:6333/dashboard

## Configuration

Required environment variables in `.env`:

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-ada-002

# News Sources
NEWS_API_KEY=your_newsapi_key

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=crypto_news

# Application Settings
MAX_RETRIEVAL_RESULTS=5
```

## Architecture

### Core Components

1. **News Ingestion Service** (`app/services/news_ingestion.py`)
   - Fetches from NewsAPI and RSS feeds
   - Processes and deduplicates articles
   - Generates embeddings and stores in Qdrant

2. **Vector Store** (`app/core/database.py`)
   - Qdrant client for semantic search
   - Handles article storage and retrieval
   - Manages collection creation and maintenance

3. **Embedding Service** (`app/core/embeddings.py`)
   - OpenAI embeddings generation
   - Fallback to HuggingFace if needed
   - Batch processing for efficiency

4. **RAG Chain** (`app/services/rag_chain.py`)
   - LangChain-based retrieval and generation
   - Conversation history integration
   - Content moderation and safety guidelines

5. **API Routes** (`app/api/routes.py`)
   - FastAPI endpoints
   - SSE streaming implementation
   - Error handling and logging

### Data Flow

1. **News Ingestion**: Background service fetches news every 2 minutes
2. **Processing**: Articles are cleaned, embedded, and stored in Qdrant
3. **Q&A**: User questions trigger semantic search and RAG generation
4. **Streaming**: Responses are streamed word-by-word via SSE

**Qdrant Connection**: Ensure Qdrant is running on the configured host/port.

**Qdrant Dashboard**: Access http://localhost:6333/dashboard to monitor the vector database, view stored articles, and debug search results.
