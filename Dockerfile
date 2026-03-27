FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies FIRST
# (Docker caches this layer — if requirements.txt doesn't change,
# this expensive step is skipped on rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your actual code
COPY . .

# Create non-root user (security best practice)
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

# Expose port for API
EXPOSE 8000

# Health check (HuggingFace Spaces requirement)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/tasks || exit 1

# The command that runs when the container starts
# Module path: customer_support_env.server.app:app
CMD ["uvicorn", "customer_support_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
