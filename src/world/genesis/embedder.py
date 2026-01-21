"""Genesis Embedder - Generate text embeddings as a tradeable service (Plan #146)

This genesis artifact provides embedding generation as a paid service:
1. Agents pay scrip to generate embeddings
2. Embeddings are used for semantic memory search
3. Cost creates incentive for agents to be selective about what they remember
"""

from __future__ import annotations

import logging
from typing import Any

from ...config import get as config_get
from ...config_schema import GenesisConfig
from ..errors import (
    ErrorCode,
    resource_error,
    validation_error,
)
from .base import GenesisArtifact

logger = logging.getLogger(__name__)


class GenesisEmbedder(GenesisArtifact):
    """
    Genesis artifact for generating text embeddings.

    This enables semantic memory by providing embedding vectors for text.
    Each embedding costs scrip, creating scarcity around what agents remember.

    Methods:
    - embed: Generate embedding for text (costs 1 scrip)
    - embed_batch: Generate embeddings for multiple texts (costs N scrip)
    """

    _embedding_model: str
    _embedding_dims: int
    _cost_per_embedding: int
    _world: Any  # World reference for kernel delegation

    def __init__(
        self,
        genesis_config: GenesisConfig | None = None,
        embedding_model: str | None = None,
        embedding_dims: int | None = None,
        cost_per_embedding: int = 1,
    ) -> None:
        """Initialize the embedder.

        Args:
            genesis_config: Optional genesis config
            embedding_model: Model for embeddings (default from config)
            embedding_dims: Embedding dimensions (default from config)
            cost_per_embedding: Scrip cost per embedding (default 1)
        """
        # Get config values
        default_model: str = config_get("memory.embedding_model") or "text-embedding-004"
        default_dims: int = config_get("memory.embedding_dims") or 768

        self._embedding_model = embedding_model or default_model
        self._embedding_dims = embedding_dims or default_dims
        self._cost_per_embedding = cost_per_embedding
        self._world = None

        artifact_id = "genesis_embedder"
        description = "Generate text embeddings for semantic search. Costs scrip per embedding."

        super().__init__(
            artifact_id=artifact_id,
            description=description
        )

        # Register methods
        self.register_method(
            name="embed",
            handler=self._embed,
            cost=self._cost_per_embedding,
            description=f"Generate embedding for text. Returns {self._embedding_dims}-dim vector. Args: [text]"
        )

        self.register_method(
            name="embed_batch",
            handler=self._embed_batch,
            cost=0,  # Cost is per-item in batch
            description="Generate embeddings for multiple texts. Args: [texts_list]. Costs 1 scrip per text."
        )

        self.register_method(
            name="get_config",
            handler=self._get_config,
            cost=0,
            description="Get embedder configuration (model, dimensions). Args: []"
        )

    def set_world(self, world: Any) -> None:
        """Set world reference for kernel delegation."""
        self._world = world

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text using LiteLLM.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception if embedding generation fails
        """
        try:
            # Use LiteLLM for embedding generation (same as llm_provider)
            import litellm

            # LiteLLM expects model format like "text-embedding-004" or "gemini/text-embedding-004"
            model = self._embedding_model
            if "/" not in model and not model.startswith("text-"):
                model = f"gemini/{model}"

            response = litellm.embedding(
                model=model,
                input=[text],
            )

            # Extract embedding from response
            if hasattr(response, 'data') and len(response.data) > 0:
                embedding = response.data[0].get("embedding", [])
                if embedding:
                    return embedding

            # Fallback: return zero vector if embedding failed
            logger.warning(f"Embedding generation returned empty for model {model}")
            return [0.0] * self._embedding_dims

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vector on error to maintain consistency
            return [0.0] * self._embedding_dims

    def _embed(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Generate embedding for text.

        Args format: [text]
        """
        if not args or len(args) < 1:
            return validation_error(
                "embed requires [text]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["text"],
            )

        text = str(args[0])

        if not text.strip():
            return validation_error(
                "Text cannot be empty",
                code=ErrorCode.INVALID_ARGUMENT,
                provided="empty string",
            )

        # Generate embedding
        try:
            embedding = self._generate_embedding(text)
            return {
                "success": True,
                "embedding": embedding,
                "dims": len(embedding),
                "model": self._embedding_model,
            }
        except Exception as e:
            return resource_error(
                f"Embedding generation failed: {e}",
                code=ErrorCode.INTERNAL_ERROR,
                error=str(e),
            )

    def _embed_batch(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Generate embeddings for multiple texts.

        Args format: [texts_list]

        Note: Caller is charged per text in the batch.
        """
        if not args or len(args) < 1:
            return validation_error(
                "embed_batch requires [texts_list]",
                code=ErrorCode.MISSING_ARGUMENT,
                required=["texts_list"],
            )

        texts = args[0]
        if not isinstance(texts, list):
            return validation_error(
                "texts_list must be a list",
                code=ErrorCode.INVALID_ARGUMENT,
                provided=type(texts).__name__,
            )

        if len(texts) == 0:
            return validation_error(
                "texts_list cannot be empty",
                code=ErrorCode.INVALID_ARGUMENT,
                provided="empty list",
            )

        # Check if caller has enough scrip for batch
        total_cost = len(texts) * self._cost_per_embedding
        if self._world is not None:
            balance = self._world.ledger.get_scrip(invoker_id)
            if balance < total_cost:
                return resource_error(
                    f"Insufficient scrip. Need {total_cost}, have {balance}",
                    code=ErrorCode.INSUFFICIENT_FUNDS,
                    required=total_cost,
                    available=balance,
                )

            # Deduct cost
            self._world.ledger.transfer(invoker_id, "genesis_embedder", total_cost)

        # Generate embeddings
        embeddings = []
        errors = []
        for i, text in enumerate(texts):
            try:
                text_str = str(text)
                if text_str.strip():
                    embedding = self._generate_embedding(text_str)
                    embeddings.append(embedding)
                else:
                    embeddings.append([0.0] * self._embedding_dims)
                    errors.append(f"Text at index {i} is empty")
            except Exception as e:
                embeddings.append([0.0] * self._embedding_dims)
                errors.append(f"Text at index {i} failed: {e}")

        result: dict[str, Any] = {
            "success": True,
            "embeddings": embeddings,
            "count": len(embeddings),
            "dims": self._embedding_dims,
            "model": self._embedding_model,
            "cost_charged": total_cost,
        }

        if errors:
            result["warnings"] = errors

        return result

    def _get_config(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get embedder configuration."""
        return {
            "success": True,
            "model": self._embedding_model,
            "dims": self._embedding_dims,
            "cost_per_embedding": self._cost_per_embedding,
        }

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for the embedder (Plan #14)."""
        return {
            "description": self.description,
            "tools": [
                {
                    "name": "embed",
                    "description": f"Generate {self._embedding_dims}-dimensional embedding for text",
                    "cost": self._cost_per_embedding,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to generate embedding for"
                            }
                        },
                        "required": ["text"]
                    }
                },
                {
                    "name": "embed_batch",
                    "description": f"Generate embeddings for multiple texts. Costs {self._cost_per_embedding} scrip per text.",
                    "cost": 0,  # Per-item cost
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "texts_list": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of texts to generate embeddings for"
                            }
                        },
                        "required": ["texts_list"]
                    }
                },
                {
                    "name": "get_config",
                    "description": "Get embedder configuration",
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        }
