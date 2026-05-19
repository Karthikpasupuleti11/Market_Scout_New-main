# app/rag/routes.py

from fastapi import APIRouter, UploadFile, File, Header
from app.rag.service import process_pdf, ask_question

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    x_session_id: str = Header(..., alias="X-Session-Id"),
):
    await process_pdf(file.file, x_session_id)
    return {"message": "PDF processed successfully"}


@router.get("/ask")
async def ask(
    query: str,
    x_session_id: str = Header(..., alias="X-Session-Id"),
):
    return await ask_question(query, x_session_id)
