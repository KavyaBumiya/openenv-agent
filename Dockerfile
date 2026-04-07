FROM python:3.11.9-slim

# Metadata labels for production tracking
LABEL maintainer="kavya.bumiya@scalerschool.dev"
LABEL version="0.1.0"
LABEL description="OpenEnv Customer Support RL Environment - Production Build"

# Set working directory
WORKDIR /app

# Install system dependencies (curl for healthcheck only)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip list | grep -E "fastapi|uvicorn|pydantic|openenv" && \
    echo "✓ Core dependencies installed"

# Copy application code
COPY . .

# Create non-root user for security (UID 1000 is standard for containers)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set Python to unbuffered for real-time logging to stdout/stderr
ENV PYTHONUNBUFFERED=1

# Expose application port
EXPOSE 7860

# Health check: ensures container is marked healthy after startup
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start FastAPI application with explicit logging
CMD ["uvicorn", "customer_support_env.server.app:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info", "--access-log"]
