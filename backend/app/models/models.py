from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """News article model"""

    title: str
    url: str
    source: str
    published_at: datetime
    content: Optional[str] = None
    summary: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model for conversation history"""

    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str = Field(..., description="The message content")
    timestamp: Optional[datetime] = None


class AskRequest(BaseModel):
    """Request model for asking questions"""

    question: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None
    chat_history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation messages")


class AskResponse(BaseModel):
    """Response model for streaming answers"""

    answer: str
    sources: List[NewsArticle]
    session_id: str
    timestamp: datetime


class LiveUpdate(BaseModel):
    """Live update model for WebSocket messages"""

    type: str = "update"
    delta: str
    sources: List[NewsArticle]
    session_id: str
    timestamp: datetime


class SubscriptionRequest(BaseModel):
    """WebSocket subscription request"""

    session_id: str
    question: str


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
