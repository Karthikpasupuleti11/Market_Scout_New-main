# app/rag/routes.py

from fastapi import APIRouter, UploadFile, File
from app.rag.service import process_pdf, ask_question

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    process_pdf(file.file)
    return {"message": "PDF processed successfully"}


@router.get("/ask")
def ask(query: str):
    return ask_question(query)