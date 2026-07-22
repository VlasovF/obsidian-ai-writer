FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
RUN uv sync --frozen --no-cache

# Copy application code
COPY scripts/ /app/scripts/
COPY src/ /app/src/
COPY tests/ /app/tests/

# Make scripts executable
RUN chmod +x /app/scripts/*.py

# Create data directories
RUN mkdir -p /app/vault/Inbox /app/vault/Templates /app/vault/_Archive

# Activate virtual environment and set Python path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Default command (will be overridden in compose)
CMD ["python", "-c", "print('Obsidian AI Writer is ready')"]