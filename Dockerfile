FROM python:3.10-slim

WORKDIR /app

# Ensure project-root packages (observability, tasks, graph, etc.) resolve in all processes
ENV PYTHONPATH=/app

# System deps for lxml, Pillow (newspaper3k), PostgreSQL, and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libxml2-dev libxslt1-dev \
    # Playwright Chromium dependencies
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libxshmfence1 libx11-xcb1 libxfixes3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Install Playwright browsers (Chromium only, no Firefox/WebKit)
RUN playwright install chromium

COPY . .

# Fail the build early if core packages were not copied into the image
RUN test -f /app/observability/metrics.py && test -f /app/tasks/pipeline_tasks.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

