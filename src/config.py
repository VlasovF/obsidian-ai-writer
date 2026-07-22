"""Configuration management using Pydantic Settings."""

import json
import logging
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Docker
    docker_prefix: str = Field(default="obsidian", alias="DOCKER_PREFIX")
    docker_network: str = Field(default="obsidian_network", alias="DOCKER_NETWORK")
    ollama_network: str = Field(default="ollama_network", alias="OLLAMA_NETWORK")

    # API
    api_port: int = Field(default=8000, alias="API_PORT")

    # Ollama
    ollama_host: str = Field(default="http://ollama:11434", alias="OLLAMA_HOST")
    ollama_embed_model: str = Field(default="mxbai-embed-large", alias="OLLAMA_EMBED_MODEL")
    ollama_llm_model: str = Field(
        default="mistral:7b-instruct-v0.3-q4_K_M", alias="OLLAMA_LLM_MODEL"
    )
    ollama_timeout: int = Field(default=60, alias="OLLAMA_TIMEOUT")

    # Qdrant
    qdrant_host: str = Field(default="qdrant", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_grpc_port: int = Field(default=6334, alias="QDRANT_GRPC_PORT")
    qdrant_collection: str = Field(default="obsidian_notes", alias="QDRANT_COLLECTION")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")

    # Redis
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    # Paths
    vault_path: Path = Field(default=Path("/app/vault"), alias="VAULT_PATH")
    inbox_path: Path = Field(default=Path("/app/vault/Inbox"), alias="INBOX_PATH")
    templates_path: Path = Field(default=Path("/app/vault/Templates"), alias="TEMPLATES_PATH")
    archive_path: Path = Field(default=Path("/app/vault/_Archive"), alias="ARCHIVE_PATH")

    # Limits
    max_files_per_batch: int = Field(default=10, alias="MAX_FILES_PER_BATCH")
    similarity_threshold: float = Field(default=0.7, alias="SIMILARITY_THRESHOLD")
    duplicate_threshold: float = Field(default=0.95, alias="DUPLICATE_THRESHOLD")
    embedding_dimension_min: int = Field(default=1000, alias="EMBEDDING_DIMENSION_MIN")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def qdrant_url(self) -> str:
        """Build Qdrant HTTP URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def qdrant_grpc_url(self) -> str:
        """Build Qdrant gRPC URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_grpc_port}"


settings = Settings()


def setup_logging() -> None:
    """Configure structured logging."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.log_format == "json":

        class JsonFormatter(logging.Formatter):
            """JSON formatter for structured logging."""

            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "name": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_data)

        handler.setFormatter(JsonFormatter())
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Reduce noise from third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
