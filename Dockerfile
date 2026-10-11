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

# Copy requirements and build all wheels into /wheels
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel --root-user-action=ignore && \
    pip wheel --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu --wheel-dir /wheels -r requirements.txt

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

# Copy application code
COPY backend/ ./backend/
COPY wsgi.py .
COPY app.py .
COPY start.sh .
COPY supervisord.conf .
# CRITICAL: alembic.ini was never copied into the image before this fix.
# alembic.ini's own script_location (`%(here)s/backend/alembic`) requires it
# to sit at /app alongside backend/. Without it, every `alembic upgrade head`
# invocation in start.sh has been silently failing (caught by `|| echo
# "Warning: ..."`) on every single container boot -- meaning the automatic
# migration step has likely never actually run in the deployed Space at all.
# Whatever kept the production schema at head was some other, out-of-band
# process (e.g. someone running alembic manually against the prod DB).
COPY alembic.ini .

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi:app
ENV PORT=7860

# Run as an unprivileged user (UID 1000, the UID Hugging Face Spaces runs containers with) so a
# compromise of anything parsing untrusted fetched HTML doesn't get root in the container.
# HOME must be writable: the embedding model is downloaded into ~/.cache on first use.
RUN useradd --create-home --uid 1000 appuser && \
    chmod +x start.sh && \
    chown -R appuser:appuser /app
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
