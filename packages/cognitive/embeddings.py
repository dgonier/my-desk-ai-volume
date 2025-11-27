"""
Embedding Service for Vector Storage.

This module provides embedding generation for the cognitive graph.
Supports multiple embedding providers:
- OpenAI (default, 1536 dimensions)
- Anthropic (via Voyage AI, 1024 dimensions)
- Local models via sentence-transformers

Usage:
    from cognitive.embeddings import get_embedder, embed_text, embed_document

    # Get singleton embedder
    embedder = get_embedder()

    # Embed single text
    embedding = await embedder.embed("Hello world")

    # Embed and chunk document
    chunks = await embed_document(
        text="Long document text...",
        title="Document Title",
        chunk_size=500
    )
"""

import os
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod


# Singleton embedder instance
_embedder_instance: Optional["BaseEmbedder"] = None


def get_embedder(provider: Optional[str] = None) -> "BaseEmbedder":
    """
    Get the singleton embedder instance.

    Args:
        provider: Override provider (openai, anthropic, openrouter, local)
                  Defaults to EMBEDDING_PROVIDER env var or "openrouter"

    Returns:
        Configured embedder instance
    """
    global _embedder_instance

    if _embedder_instance is None:
        provider = provider or os.environ.get("EMBEDDING_PROVIDER", "openrouter")

        if provider == "openai":
            _embedder_instance = OpenAIEmbedder()
        elif provider == "anthropic":
            _embedder_instance = VoyageEmbedder()
        elif provider == "openrouter":
            _embedder_instance = OpenRouterEmbedder()
        elif provider == "local":
            _embedder_instance = LocalEmbedder()
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")

    return _embedder_instance


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Embed a single text string."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in batch."""
        pass


class OpenAIEmbedder(BaseEmbedder):
    """
    OpenAI embedding provider using text-embedding-3-small.

    Requires OPENAI_API_KEY environment variable.
    Produces 1536-dimensional embeddings.
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        self._model = model
        self._dimensions = 1536
        self._client = None

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI()
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    async def embed(self, text: str) -> List[float]:
        """Embed a single text string."""
        response = await self.client.embeddings.create(
            input=text,
            model=self._model
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in batch."""
        # OpenAI supports up to 2048 inputs per request
        response = await self.client.embeddings.create(
            input=texts,
            model=self._model
        )
        return [item.embedding for item in response.data]


class VoyageEmbedder(BaseEmbedder):
    """
    Voyage AI embedding provider (recommended by Anthropic).

    Requires VOYAGE_API_KEY environment variable.
    Produces 1024-dimensional embeddings with voyage-2.
    """

    def __init__(self, model: str = "voyage-2"):
        self._model = model
        self._dimensions = 1024
        self._client = None

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def client(self):
        """Lazy-load the Voyage client."""
        if self._client is None:
            try:
                import voyageai
                self._client = voyageai.AsyncClient()
            except ImportError:
                raise ImportError("voyageai package required. Install with: pip install voyageai")
        return self._client

    async def embed(self, text: str) -> List[float]:
        """Embed a single text string."""
        result = await self.client.embed(
            texts=[text],
            model=self._model
        )
        return result.embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in batch."""
        result = await self.client.embed(
            texts=texts,
            model=self._model
        )
        return result.embeddings


class LocalEmbedder(BaseEmbedder):
    """
    Local embedding using sentence-transformers.

    No API key required, runs locally.
    Default model: all-MiniLM-L6-v2 (384 dimensions)
    """

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self._model_name = model
        self._model = None
        self._dimensions = 384  # Default for MiniLM

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                self._dimensions = self._model.get_sentence_embedding_dimension()
            except ImportError:
                raise ImportError(
                    "sentence-transformers package required. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    async def embed(self, text: str) -> List[float]:
        """Embed a single text string."""
        # sentence-transformers is sync, but we wrap for consistency
        embedding = self.model.encode(text)
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in batch."""
        embeddings = self.model.encode(texts)
        return [e.tolist() for e in embeddings]


class OpenRouterEmbedder(BaseEmbedder):
    """
    OpenRouter embedding provider.

    Requires OPENROUTER_API_KEY environment variable.
    Default model: qwen/qwen3-embedding-8b

    OpenRouter provides access to various embedding models through a unified API.
    """

    def __init__(self, model: Optional[str] = None):
        self._model = model or os.environ.get("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
        self._api_key = os.environ.get("OPENROUTER_API_KEY")
        self._base_url = "https://openrouter.ai/api/v1"
        self._dimensions = 4096  # Qwen3-embedding-8b default, will be updated on first call
        self._client = None

        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable required")

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def client(self):
        """Lazy-load the httpx async client."""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    base_url=self._base_url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://my-desk.ai",
                        "X-Title": "my-desk.ai"
                    },
                    timeout=60.0
                )
            except ImportError:
                raise ImportError("httpx package required. Install with: pip install httpx")
        return self._client

    async def embed(self, text: str) -> List[float]:
        """Embed a single text string."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts in batch.

        OpenRouter uses the same API format as OpenAI for embeddings.
        """
        response = await self.client.post(
            "/embeddings",
            json={
                "model": self._model,
                "input": texts
            }
        )

        if response.status_code != 200:
            error_detail = response.text
            raise Exception(f"OpenRouter embedding failed: {response.status_code} - {error_detail}")

        data = response.json()

        # Extract embeddings from response
        embeddings = []
        for item in data.get("data", []):
            embedding = item.get("embedding", [])
            embeddings.append(embedding)

            # Update dimensions on first successful call
            if embedding and self._dimensions != len(embedding):
                self._dimensions = len(embedding)

        return embeddings

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# ============================================
# High-Level Functions
# ============================================

async def embed_text(text: str, provider: Optional[str] = None) -> List[float]:
    """
    Embed a single text string.

    Args:
        text: Text to embed
        provider: Optional provider override

    Returns:
        Embedding vector
    """
    embedder = get_embedder(provider)
    return await embedder.embed(text)


async def embed_texts(texts: List[str], provider: Optional[str] = None) -> List[List[float]]:
    """
    Embed multiple texts in batch.

    Args:
        texts: List of texts to embed
        provider: Optional provider override

    Returns:
        List of embedding vectors
    """
    embedder = get_embedder(provider)
    return await embedder.embed_batch(texts)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separator: str = "\n"
) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: Full text to chunk
        chunk_size: Target characters per chunk
        chunk_overlap: Overlap between chunks
        separator: Preferred split point

    Returns:
        List of chunk dicts with text and metadata
    """
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        # Find end of this chunk
        end = start + chunk_size

        # If not at the end, try to break at separator
        if end < len(text):
            # Look for separator in the overlap region
            search_start = max(start + chunk_size - chunk_overlap, start)
            sep_pos = text.rfind(separator, search_start, end)
            if sep_pos > start:
                end = sep_pos + len(separator)

        chunk_text = text[start:end].strip()

        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "chunk_index": chunk_index,
                "start_char": start,
                "end_char": end,
                "char_count": len(chunk_text)
            })
            chunk_index += 1

        # Move start, accounting for overlap
        start = end - chunk_overlap if end < len(text) else end

    return chunks


async def embed_document(
    text: str,
    title: Optional[str] = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    metadata: Optional[Dict[str, Any]] = None,
    provider: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Chunk and embed a document.

    Args:
        text: Full document text
        title: Optional document title
        chunk_size: Characters per chunk
        chunk_overlap: Overlap between chunks
        metadata: Additional metadata for all chunks
        provider: Embedding provider override

    Returns:
        List of chunks with embeddings
    """
    # Chunk the text
    chunks = chunk_text(text, chunk_size, chunk_overlap)

    if not chunks:
        return []

    # Get embeddings for all chunks
    texts = [c["text"] for c in chunks]
    embeddings = await embed_texts(texts, provider)

    # Add embeddings and metadata to chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
        chunk["title"] = title
        if metadata:
            chunk.update(metadata)

    return chunks


async def store_document_chunks(
    graph,  # CognitiveGraph instance
    text: str,
    title: str,
    source_url: Optional[str] = None,
    doc_type: Optional[str] = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Chunk, embed, and store a document in the graph.

    This is the main entry point for adding documents to the
    knowledge base with vector search support.

    Args:
        graph: CognitiveGraph instance
        text: Full document text
        title: Document title
        source_url: Optional source URL
        doc_type: Document type (article, pdf, etc.)
        chunk_size: Characters per chunk
        chunk_overlap: Overlap between chunks
        provider: Embedding provider override

    Returns:
        Dict with document_id and chunk_ids
    """
    from datetime import datetime

    # Create document node
    doc_props = {
        "title": title,
        "content": text,
        "source_url": source_url,
        "doc_type": doc_type,
        "char_count": len(text),
        "word_count": len(text.split()),
        "created_at": datetime.utcnow().isoformat()
    }

    doc_query = """
    CREATE (d:Document $props)
    RETURN d, elementId(d) as id
    """

    with graph.session() as session:
        result = session.run(doc_query, props=doc_props)
        record = result.single()
        document_id = record["id"]

    # Chunk and embed
    chunks = await embed_document(
        text=text,
        title=title,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        provider=provider
    )

    # Store chunks
    chunk_ids = []
    for chunk in chunks:
        chunk_node = graph.store_chunk_with_embedding(
            text=chunk["text"],
            embedding=chunk["embedding"],
            source_id=document_id,
            chunk_index=chunk["chunk_index"],
            metadata={
                "title": title,
                "start_char": chunk["start_char"],
                "end_char": chunk["end_char"]
            }
        )
        chunk_ids.append(chunk_node["id"])

    return {
        "document_id": document_id,
        "chunk_ids": chunk_ids,
        "chunk_count": len(chunk_ids)
    }
