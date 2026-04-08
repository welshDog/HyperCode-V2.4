import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.rag import rag
from app.api import deps
from app.models import models

logger = logging.getLogger(__name__)

router = APIRouter()

class IngestRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    source: str = Field(min_length=1, max_length=200)
    metadata: Optional[dict] = None

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)

@router.post("/ingest", response_model=dict)
def ingest_memory(
    request: IngestRequest,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Ingest text into the vector memory.
    """
    try:
        # Privacy-first: scope ingested memory to the authenticated user by default.
        # This prevents cross-user retrieval when the memory store is shared.
        meta = dict(request.metadata or {})
        meta.setdefault("visibility", "private")
        meta["user_id"] = current_user.id
        chunks_count = rag.ingest_document(request.content, request.source, meta)
    except Exception as e:
        logger.error(f"ChromaDB ingest failed: {e}")
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    if chunks_count == 0:
        raise HTTPException(status_code=500, detail="Failed to ingest document")
    return {"status": "success", "chunks_ingested": chunks_count}

@router.post("/query", response_model=dict)
def query_memory(
    request: QueryRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Semantic search in vector memory.
    """
    try:
        # Privacy-first: non-superusers can only query their own memory.
        filters = None if current_user.is_superuser else {"user_id": current_user.id}
        results = rag.query(request.query, request.limit, filters=filters)
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    return {"results": results}

@router.post("/reset", response_model=dict)
def reset_memory(
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Wipe all memory.
    """
    try:
        rag.reset()
    except Exception as e:
        logger.error(f"ChromaDB reset failed: {e}")
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    return {"status": "memory_wiped"}
