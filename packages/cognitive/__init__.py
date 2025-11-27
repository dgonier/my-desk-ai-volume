"""
Cognitive Package - Neo4j Graph Database Foundation

This is the core package that provides graph database connectivity
for the cognitive tree architecture. All other packages (relationships,
research, comms) use this for persistent storage.

Graph Structure:
- Core: User, Assistant (always present)
- Cycles: Self-assigned tasks toward goals
- Projects: Larger endeavors with chapters, drafts
- Knowledge: Chunks, Entities with vector embeddings
- Research: Articles, Jobs, Topics, Sources

Key Concepts:
- The graph always starts with User + Assistant nodes connected by ASSISTS
- Cycles are how the agent organizes autonomous work
- Vector indexes enable semantic search (requires Neo4j 5.11+)

Embedding Support:
- OpenAI text-embedding-3-small (default)
- Voyage AI (Anthropic recommended)
- Local sentence-transformers

Usage:
    from cognitive import get_graph, embed_text, store_document_chunks

    graph = get_graph()

    # Initialize with user and assistant
    user, assistant = graph.initialize_graph(
        user_first_name="John",
        user_last_name="Doe"
    )

    # Create a cycle for autonomous work
    cycle = graph.create_cycle(
        name="Research AI Agents",
        objective="Understand current state of AI agent architectures",
        cycle_type=CycleType.RESEARCH
    )

    # Store document with embeddings
    result = await store_document_chunks(
        graph,
        text="Long document...",
        title="AI Agents Overview"
    )
"""

from .graph import CognitiveGraph, get_graph
from .models import (
    # Base models
    Node, Relationship, NodeType, RelationType,
    # Identity nodes
    UserNode, AssistantNode,
    # Cycle and project models
    CycleNode, CycleStatus, CycleType,
    ProjectNode, ProjectCategory, ChapterNode, DraftNode,
    TaskNode, GoalNode, InsightNode,
    # Vector/RAG models
    ChunkNode, EntityNode, DocumentNode,
    # Research models
    ArticleNode, JobNode, TopicNode,
    # Comms models
    ConversationNode,
    # Persona Identity models
    PersonaNode, TraitNode, MemoryNode, PreferenceNode,
)
from .embeddings import (
    get_embedder,
    embed_text,
    embed_texts,
    embed_document,
    chunk_text,
    store_document_chunks,
    BaseEmbedder,
    OpenAIEmbedder,
    VoyageEmbedder,
    OpenRouterEmbedder,
    LocalEmbedder,
)

__all__ = [
    # Core
    "CognitiveGraph",
    "get_graph",
    "Node",
    "Relationship",
    "NodeType",
    "RelationType",
    # Identity
    "UserNode",
    "AssistantNode",
    # Cycles
    "CycleNode",
    "CycleStatus",
    "CycleType",
    # Projects
    "ProjectNode",
    "ProjectCategory",
    "ChapterNode",
    "DraftNode",
    "TaskNode",
    "GoalNode",
    "InsightNode",
    # Vector/RAG
    "ChunkNode",
    "EntityNode",
    "DocumentNode",
    # Research
    "ArticleNode",
    "JobNode",
    "TopicNode",
    # Comms
    "ConversationNode",
    # Persona Identity
    "PersonaNode",
    "TraitNode",
    "MemoryNode",
    "PreferenceNode",
    # Embeddings
    "get_embedder",
    "embed_text",
    "embed_texts",
    "embed_document",
    "chunk_text",
    "store_document_chunks",
    "BaseEmbedder",
    "OpenAIEmbedder",
    "VoyageEmbedder",
    "OpenRouterEmbedder",
    "LocalEmbedder",
]
