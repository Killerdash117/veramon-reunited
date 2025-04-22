# Stage 1: Builder stage
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements (for better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.10-slim

# Create non-root user for security
RUN groupadd -r veramon && useradd -r -g veramon -m -s /bin/bash veramon

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /home/veramon/.local
ENV PATH=/home/veramon/.local/bin:$PATH

# Create necessary directories for battle system, trades, faction, event systems and data persistence
RUN mkdir -p /app/data/battles /app/data/trades /app/data/backups /app/data/quests /app/data/factions /app/data/events /app/logs \
    && chown -R veramon:veramon /app

# Copy application code
COPY --chown=veramon:veramon src/ /app/src/

# Create required data files with proper ownership
RUN touch /app/data/veramon_reunited.db && chown veramon:veramon /app/data/veramon_reunited.db

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/veramon/.local/bin:$PATH"

# Switch to non-root user
USER veramon

# Create volume mount points for persistence
VOLUME ["/app/data", "/app/logs"]

# Health check for Discord connection
HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import socket; socket.socket().connect(('discord.com', 443))"

# Run the bot
CMD ["python", "-m", "src.main"]
