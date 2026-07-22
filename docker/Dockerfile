FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./

RUN uv venv /app/.venv
RUN uv sync --frozen --no-cache

COPY scripts/ /app/scripts/
COPY src/ /app/src/

RUN chmod +x /app/scripts/*.py

RUN mkdir -p /app/vault/Inbox /app/vault/Templates /app/vault/_Archive

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Copy .env file if present
COPY .env* /app/

CMD ["python", "-c", "print('Obsidian AI Writer is ready')"]