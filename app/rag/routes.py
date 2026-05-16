# app/rag/routes.py

from fastapi import APIRouter, UploadFile, File
from app.rag.service import process_pdf, ask_question

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    await process_pdf(file.file)
    return {"message": "PDF processed successfully"}


@router.get("/ask")
async def ask(query: str):
    return await ask_question(query)