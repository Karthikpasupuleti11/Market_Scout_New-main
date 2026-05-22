# app/rag/routes.py

from fastapi import APIRouter, UploadFile, File, Header
from pydantic import BaseModel
from typing import Optional
from app.rag.service import process_pdf, process_report, ask_question

router = APIRouter(prefix="/rag", tags=["RAG"])


class ReportIndexRequest(BaseModel):
    """Accepts a structured report JSON for RAG indexing."""
    report: dict
    session_id: Optional[str] = None


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    x_session_id: str = Header(..., alias="X-Session-Id"),
):
    await process_pdf(file.file, x_session_id)
    return {"message": "PDF processed successfully"}


@router.post("/index")
async def index_report(body: ReportIndexRequest):
    """Index a structured JSON report into the RAG vector store."""
    session_id = body.session_id or "default"
    await process_report(body.report, session_id)
    return {"message": "Report indexed successfully", "session_id": session_id}


@router.get("/ask")
async def ask(
    query: str,
    x_session_id: str = Header(..., alias="X-Session-Id"),
):
    return await ask_question(query, x_session_id)
