import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.services.news_ingestion import news_service

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Crypto News Agent Backend")
    print("Initializing services...")

    # Start background news ingestion
    print("Starting news ingestion service...")
    asyncio.create_task(news_service.start_ingestion())

    yield
    # Shutdown
    print("Shutting down Crypto News Agent Backend")


app = FastAPI(
    title="Crypto News Agent API",
    description="Real-time crypto news Q&A with live updates",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.core.database import vector_store
    from app.services.news_ingestion import news_service

    try:
        article_count = await vector_store.get_article_count()
        ingestion_stats = await news_service.get_ingestion_stats()

        return {
            "status": "healthy",
            "service": "crypto-news-agent",
            "database": {"articles": article_count, "status": "connected"},
            "ingestion": ingestion_stats,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "crypto-news-agent",
            "database": {"articles": 0, "status": "error", "error": str(e)},
            "ingestion": {"error": str(e)},
        }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Crypto News Agent API",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
