FROM python:3.10-slim

WORKDIR /app

# System deps for lxml, Pillow (newspaper3k), and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
