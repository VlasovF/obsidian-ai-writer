"""Custom exceptions for the application."""


class ObsidianAIError(Exception):
    """Base exception for all application errors."""

    pass


class ConfigurationError(ObsidianAIError):
    """Raised when configuration is invalid."""

    pass


class ServiceUnavailableError(ObsidianAIError):
    """Raised when an external service is unavailable."""

    def __init__(self, service: str, reason: str = ""):
        self.service = service
        self.reason = reason
        super().__init__(f"Service {service} unavailable: {reason}")


class EmbeddingError(ObsidianAIError):
    """Raised when embedding generation fails."""

    pass


class QdrantError(ObsidianAIError):
    """Raised when Qdrant operations fail."""

    pass


class FileProcessingError(ObsidianAIError):
    """Raised when file processing fails."""

    pass


class DeduplicationError(ObsidianAIError):
    """Raised when duplicate detection fails."""

    pass


class LLMGenerationError(ObsidianAIError):
    """Raised when LLM text generation fails."""

    pass
