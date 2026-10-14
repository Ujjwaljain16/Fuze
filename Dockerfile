# =============================================================================
# FUZE — Multi-Stage Docker Build
# Trigger HF Rebuild: 1
# =============================================================================
# Stage 1 (builder): compile all Python wheels
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

# Build wheels for exactly the locked set: every download must match its hash in
# requirements.lock (regenerate with scripts/lock-requirements.sh).
COPY requirements.lock .
RUN pip install --upgrade pip --root-user-action=ignore && \
    pip wheel --no-cache-dir --require-hashes --no-deps --wheel-dir /wheels -r requirements.lock

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
# The lock is complete (all transitive deps), so install the built wheels as-is.
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --no-deps /wheels/*.whl --root-user-action=ignore && \
    rm -rf /wheels

# Run as an unprivileged user (UID 1000, the UID Hugging Face Spaces runs containers with) so a
# compromise of anything parsing untrusted fetched HTML doesn't get root in the container.
# Created before the model download so the model files are owned by it in the same layer.
RUN useradd --create-home --uid 1000 appuser

# Bake the embedding model (DEFAULT_EMBEDDING_MODEL in backend/utils/embedding_utils.py) and the small
# cross-encoder that marks weak recommendations (backend/utils/reranker.py, about 90 MB) into
# the image. Otherwise every new container downloads it on first use: slow cold starts, and a
# Hub outage means embeddings fail (EmbeddingUnavailable) until it recovers. This layer sits above the app code, so
# code changes don't download it again; the chown in the same RUN avoids a second copy of the
# model in a later layer.
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('BAAI/bge-small-en-v1.5'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')" && \
    chown -R appuser:appuser /app/.cache

# Copy application code
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser wsgi.py .
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser start.sh .
COPY --chown=appuser:appuser supervisord.conf .
COPY --chown=appuser:appuser gunicorn.conf.py .
# alembic.ini's script_location (`%(here)s/backend/alembic`) needs it at /app next to
# backend/. start.sh runs `alembic upgrade head` and exits if it fails.
COPY --chown=appuser:appuser alembic.ini .

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi:app
ENV PORT=7860
# Never reach out to the Hub at run time: the model baked in above is all production loads.
# Changing EMBEDDING_MODEL_NAME or SEARCH_RERANK_MODEL needs another model: bake
# it in the same way (or run with HF_HUB_OFFLINE=0), or loading it fails and the app falls back.
ENV HF_HUB_OFFLINE=1

RUN chmod +x start.sh && \
    chown appuser:appuser /app
USER appuser
ENV HOME=/home/appuser

EXPOSE 7860

# Checks liveness (process alive + Flask responding), not readiness (DB/Redis
# reachable) -- a transient DB/Redis blip shouldn't cause Docker to restart an
# otherwise-healthy container; that's what /health/readiness is for, used by
# orchestration layers that route traffic rather than restart the process.
# start-period gives gunicorn + the RQ workers + (now-actually-running)
# migrations time to boot before the first check counts against it.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:${PORT}/health/liveness', timeout=3).status==200 else 1)" || exit 1

CMD ["./start.sh"]
