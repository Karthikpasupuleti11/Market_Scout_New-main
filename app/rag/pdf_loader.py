# app/rag/pdf_loader.py

from PyPDF2 import PdfReader

def load_pdf(file):
    reader = PdfReader(file)
    pages = []

    for i, page in enumerate(reader.pages):
        content = page.extract_text()
        if content:
            pages.append({
                "page": i + 1,
                "text": content
            })

    return pages