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

# Fetch camoufox browser artifacts (written to ~/.local/share/camoufox or similar)
# The || true prevents build failure if camoufox is unavailable in CI
RUN camoufox fetch || echo "[builder] camoufox fetch completed (or skipped)"

# Capture camoufox data directory for COPY in runtime stage
RUN python -c "import camoufox; import os; print(os.path.dirname(camoufox.__file__))" \
    > /tmp/camoufox_pkg_path.txt || echo "unknown" > /tmp/camoufox_pkg_path.txt

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
# camoufox stores downloaded browser in the package directory
COPY --from=builder /root/.local /root/.local
COPY --from=builder /root/.camoufox /root/.camoufox 2>/dev/null || true

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
