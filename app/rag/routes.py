# app/rag/routes.py

from fastapi import APIRouter, UploadFile, File, Header
from pydantic import BaseModel
from typing import List, Optional
from app.rag.service import process_pdf, process_report_text, ask_question

router = APIRouter(prefix="/rag", tags=["RAG"])


class IndexReportRequest(BaseModel):
    """Request body for indexing a report's text content into the RAG vector store."""
    company_name: str
    executive_summary: str = ""
    features: List[dict] = []
    all_sources: List[str] = []


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    x_session_id: str = Header(..., alias="X-Session-Id"),
):
    await process_pdf(file.file, x_session_id)
    return {"message": "PDF processed successfully"}


@router.post("/index-report")
async def index_report(
    req: IndexReportRequest,
    x_session_id: str = Header(..., alias="X-Session-Id"),
):
    """Convert a report's structured data into text, chunk it, embed it,
    and store in the vector store — ready for RAG queries."""
    process_report_text(
        company_name=req.company_name,
        executive_summary=req.executive_summary,
        features=req.features,
        all_sources=req.all_sources,
        session_id=x_session_id,
    )
    return {"message": "Report indexed successfully", "company": req.company_name}


@router.get("/ask")
async def ask(
    query: str,
    x_session_id: str = Header(..., alias="X-Session-Id"),
):
    return await ask_question(query, x_session_id)
