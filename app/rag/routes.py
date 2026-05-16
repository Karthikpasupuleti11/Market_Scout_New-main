# app/rag/routes.py

from fastapi import APIRouter, UploadFile, File
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
async def upload_pdf(file: UploadFile = File(...)):
    await process_pdf(file.file)
    return {"message": "PDF processed successfully"}


@router.post("/index-report")
def index_report(req: IndexReportRequest):
    """Convert a report's structured data into text, chunk it, embed it,
    and store in the vector store — ready for RAG queries."""
    process_report_text(
        company_name=req.company_name,
        executive_summary=req.executive_summary,
        features=req.features,
        all_sources=req.all_sources,
    )
    return {"message": "Report indexed successfully", "company": req.company_name}


@router.get("/ask")
async def ask(query: str):
    return await ask_question(query)