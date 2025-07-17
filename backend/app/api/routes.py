import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.models import AskRequest
from app.services.rag_chain import rag_chain

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ask")
async def ask_question(request: AskRequest):
    """Ask a question about crypto news with streaming response"""
    try:
        # generate session id if not provided
        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"Starting Q&A session {session_id} for question: '{request.question[:50]}...'")

        async def generate_stream() -> AsyncGenerator[dict, None]:
            try:
                logger.info(f"Processing question for session {session_id}")
                # get answer from rag chain with chat history
                chat_history = []
                if request.chat_history:
                    chat_history = [msg.dict() for msg in request.chat_history]
                    logger.info(f"Session {session_id}: Received {len(chat_history)} previous messages")
                else:
                    logger.info(f"Session {session_id}: No previous conversation history")

                result = await rag_chain.answer_question(request.question, chat_history)
                logger.info(f"RAG chain completed for session {session_id}, found {len(result['sources'])} sources")

                # stream answer in chunks
                answer = result["answer"]
                chunk_size = 50  # chars per chunk
                total_chunks = (len(answer) + chunk_size - 1) // chunk_size
                logger.info(
                    f"Streaming answer for session {session_id}: {total_chunks} chunks, {len(answer)} characters"
                )

                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i : i + chunk_size]
                    chunk_num = (i // chunk_size) + 1
                    logger.debug(f"Session {session_id}: Sending chunk {chunk_num}/{total_chunks}: '{chunk[:30]}...'")
                    yield {
                        "event": "answer_chunk",
                        "data": json.dumps(
                            {"chunk": chunk, "session_id": session_id, "is_complete": i + chunk_size >= len(answer)}
                        ),
                    }
                    await asyncio.sleep(0.1)  # small delay for streaming effect

                # send final response with sources
                sources_data = []
                for source in result["sources"]:
                    source_dict = source.dict()
                    # ensure published_at is serialized as iso string
                    if "published_at" in source_dict and isinstance(source_dict["published_at"], datetime):
                        source_dict["published_at"] = source_dict["published_at"].isoformat()
                    sources_data.append(source_dict)

                logger.info(f"Session {session_id}: Sending completion with {len(sources_data)} sources")
                yield {
                    "event": "answer_complete",
                    "data": json.dumps(
                        {
                            "sources": sources_data,
                            "session_id": session_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                }
                logger.info(f"Session {session_id}: Stream completed successfully")

            except Exception as e:
                logger.error(f"Error in stream generation for session {session_id}: {e}", exc_info=True)
                yield {"event": "error", "data": json.dumps({"error": str(e)})}

        return EventSourceResponse(generate_stream())

    except Exception as e:
        logger.error(f"Error setting up Q&A stream for question '{request.question[:50]}...': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
