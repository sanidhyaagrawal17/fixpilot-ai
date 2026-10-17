# Polyglot Production Container for FixPilot
# Python 3.11 + Node.js (for JS/TS sandbox) + Git (for shallow repository inspection)
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# 1. Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Create isolated non-root execution user
RUN useradd -m -u 1000 fixpilot && chown -R fixpilot:fixpilot /app

# 3. Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 4. Copy codebase and set non-root ownership
COPY --chown=fixpilot:fixpilot . .

# 5. Switch to non-root user for container-level sandbox isolation
USER fixpilot

EXPOSE 8000

# 6. Container healthcheck mapped to dynamic port
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# 7. Start ASGI server with keep-alive buffer flushing
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 120 --workers 2"]
