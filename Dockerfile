# =============================================================================
# FUZE — Multi-Stage Docker Build
# =============================================================================
# Stage 1 (builder): compile all Python wheels, fetch camoufox browser
# Stage 2 (runtime): copy only compiled wheels + app code — no build toolchain
#
# Target: Hugging Face Spaces (port 7860)
# Expected image size reduction: ~35-45% vs single-stage
# =============================================================================

# ---------------------------------------------------------------------------
# STAGE 1 — builder
# ---------------------------------------------------------------------------
FROM python:3.11 AS builder

WORKDIR /build

# Install build-time system dependencies (compilers, headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and build all wheels into /wheels
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel --root-user-action=ignore && \
    pip wheel --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu --wheel-dir /wheels -r requirements.txt

# Install packages into builder so we can run camoufox fetch
RUN pip install --no-cache-dir --no-index --find-links /wheels -r requirements.txt \
    --root-user-action=ignore

# Fetch camoufox browser artifacts
RUN mkdir -p /root/.cache/camoufox && \
    camoufox fetch || echo "[builder] camoufox fetch completed (or skipped)"

# ---------------------------------------------------------------------------
# STAGE 2 — runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime-only system dependencies (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    postgresql-client \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built wheels from builder and install without index (no network needed)
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links /wheels -r requirements.txt \
    --root-user-action=ignore && \
    rm -rf /wheels

# Copy camoufox browser data from builder
COPY --from=builder /root/.cache/camoufox /root/.cache/camoufox

# Copy application code
COPY backend/ ./backend/
COPY wsgi.py .
COPY app.py .
COPY start.sh .
COPY supervisord.conf .

# Environment
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi:app
ENV PORT=7860

RUN chmod +x start.sh

EXPOSE 7860

CMD ["./start.sh"]
