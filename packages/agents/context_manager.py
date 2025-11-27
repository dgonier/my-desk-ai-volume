"""
Context Manager for Persona Agent

Handles efficient retrieval and injection of context into conversations.

ARCHITECTURE NOTES (for future iteration):
==========================================

Current Implementation (v0.1 - Simple):
- Core identity: Always loaded (small, ~500 tokens)
- Traits: Always loaded (small, ~200 tokens)
- Memories: Retrieved by embedding similarity (top-k)
- Preferences: Loaded by category
- Project context: Passed in from caller

Future Iterations to Consider:
------------------------------

1. MEMORY RETRIEVAL (High Priority)
   - Current: Simple top-k embedding similarity
   - Future:
     * Hybrid search (embedding + keyword/BM25)
     * Temporal weighting (recent memories more relevant)
     * Usage tracking (frequently useful memories bubble up)
     * Memory consolidation (merge similar memories)
     * Episodic vs semantic memory distinction
     * Memory importance scoring
     * Forgetting curve simulation

2. CONTEXT WINDOW OPTIMIZATION
   - Current: Fixed token budget per category
   - Future:
     * Dynamic budget based on conversation complexity
     * Sliding context window with summarization
     * Hierarchical summarization of old context
     * Smart truncation (keep important parts)

3. RELEVANCE SCORING
   - Current: Cosine similarity only
   - Future:
     * Multi-factor relevance (recency, importance, usage)
     * User feedback loop (was this memory helpful?)
     * Context-aware relevance (what's the user doing?)
     * Entity-based retrieval (mentioned people/projects)

4. CACHING
   - Current: None
   - Future:
     * Cache embeddings for common queries
     * Cache retrieved context for conversation continuity
     * Invalidate on memory updates

5. PREFERENCE LEARNING
   - Current: Simple category lookup
   - Future:
     * Confidence-weighted preferences
     * Preference decay over time
     * Conflict resolution between preferences
     * Explicit vs inferred preference handling

6. GRAPH TRAVERSAL
   - Current: Direct node lookup
   - Future:
     * Multi-hop reasoning (person -> project -> related memories)
     * Relationship-aware context (family vs work contexts)
     * Subgraph extraction for complex queries

7. CONVERSATION HISTORY
   - Current: Passed from caller, not managed
   - Future:
     * Automatic summarization of long conversations
     * Key fact extraction from history
     * Cross-conversation memory formation

TODOs for immediate improvement:
--------------------------------
- [ ] Add embedding cache
- [ ] Implement memory usage tracking
- [ ] Add temporal decay to memory retrieval
- [ ] Support entity-based memory lookup
- [ ] Add preference confidence thresholds
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContextBudget:
    """
    Token budget for different context categories.

    ITERATION NOTE: These are rough estimates. Future versions should:
    - Dynamically adjust based on conversation needs
    - Actually count tokens instead of estimating
    - Allow user/admin configuration
    """
    core_identity: int = 500      # Name, tagline, values, style
    traits: int = 300             # Personality traits
    memories: int = 800           # Retrieved memories
    preferences: int = 300        # User preferences
    project_context: int = 500    # Current project info
    user_context: int = 300       # User info

    @property
    def total(self) -> int:
        return (self.core_identity + self.traits + self.memories +
                self.preferences + self.project_context + self.user_context)


@dataclass
class RetrievedContext:
    """
    Container for all retrieved context.

    ITERATION NOTE: Consider adding:
    - Retrieval timestamps for debugging
    - Relevance scores for each piece
    - Source tracking (which query retrieved what)
    - Token counts per section
    """
    core_identity: Dict[str, Any] = field(default_factory=dict)
    traits: List[Dict[str, Any]] = field(default_factory=list)
    memories: List[Dict[str, Any]] = field(default_factory=list)
    preferences: List[Dict[str, Any]] = field(default_factory=list)
    project_context: Optional[Dict[str, Any]] = None
    user_context: Optional[Dict[str, Any]] = None

    # Metadata for debugging/iteration
    retrieval_timestamp: Optional[str] = None
    memory_query_used: Optional[str] = None
    memories_considered: int = 0

    def to_system_prompt(self) -> str:
        """
        Build system prompt from retrieved context.

        ITERATION NOTE: This is a simple template. Future versions could:
        - Use dynamic templates based on conversation type
        - Adjust verbosity based on available budget
        - Include/exclude sections based on relevance
        """
        sections = []

        # Core identity (always included)
        identity = self.core_identity
        name = identity.get('name', 'Assistant')
        tagline = identity.get('tagline', 'your helpful companion')

        sections.append(f"You are {name}, {tagline}.")

        if identity.get('personality_summary'):
            sections.append(identity['personality_summary'])

        # Values
        values = identity.get('core_values', [])
        if values:
            sections.append(f"Core values: {', '.join(values)}")

        # Communication style
        style = identity.get('communication_style', 'conversational')
        sections.append(f"Communication style: {style}")

        # Traits
        if self.traits:
            trait_lines = [f"- {t.get('name', 'Unknown')}: {t.get('description', '')}"
                         for t in self.traits[:5]]  # Limit to top 5
            sections.append("Personality traits:\n" + "\n".join(trait_lines))

        # Memories (contextually retrieved)
        # ITERATION NOTE: This is where smart retrieval matters most
        if self.memories:
            memory_lines = []
            for m in self.memories[:3]:  # Limit to top 3 most relevant
                content = m.get('content', '')[:200]  # Truncate long memories
                memory_lines.append(f"- {content}")
            sections.append("Relevant memories/observations:\n" + "\n".join(memory_lines))

        # Preferences
        if self.preferences:
            pref_lines = [f"- {p.get('name', '')}: {p.get('value', '')}"
                        for p in self.preferences[:5]]
            sections.append("User preferences:\n" + "\n".join(pref_lines))

        # User context
        if self.user_context:
            user_name = self.user_context.get('name', 'the user')
            sections.append(f"You are assisting {user_name}.")

        # Project context
        if self.project_context:
            proj_name = self.project_context.get('name', 'Unknown')
            proj_desc = self.project_context.get('description', '')[:200]
            sections.append(f"Current project: {proj_name}\n{proj_desc}")

        # Identity reminder
        sections.append(f"\nRemember: You ARE {name}. Speak authentically as yourself.")

        return "\n\n".join(sections)


class ContextManager:
    """
    Manages context retrieval for the Persona Agent.

    ITERATION NOTE: This is v0.1 - intentionally simple.
    See module docstring for future iteration plans.
    """

    def __init__(self, graph=None, embedder=None):
        """
        Initialize context manager.

        Args:
            graph: CognitiveGraph instance (lazy loaded if None)
            embedder: Embedding provider (lazy loaded if None)
        """
        self._graph = graph
        self._embedder = embedder
        self._persona_id: Optional[str] = None
        self._core_identity_cache: Optional[Dict[str, Any]] = None

    @property
    def graph(self):
        """Lazy load graph connection."""
        if self._graph is None:
            from ..cognitive.graph import get_graph
            self._graph = get_graph()
        return self._graph

    @property
    def embedder(self):
        """Lazy load embedder."""
        if self._embedder is None:
            from ..cognitive.embeddings import get_embedder
            self._embedder = get_embedder()
        return self._embedder

    async def get_context(
        self,
        query: str,
        project_context: Optional[Dict[str, Any]] = None,
        preference_categories: Optional[List[str]] = None,
        budget: Optional[ContextBudget] = None,
        memory_limit: int = 5
    ) -> RetrievedContext:
        """
        Retrieve relevant context for a conversation.

        Args:
            query: The user's message (used for memory retrieval)
            project_context: Optional project info to include
            preference_categories: Which preference categories to load
            budget: Token budget (not enforced in v0.1)
            memory_limit: Max memories to retrieve

        Returns:
            RetrievedContext with all relevant information

        ITERATION NOTE:
        - query is used to find relevant memories via embedding similarity
        - Future: also extract entities from query for graph traversal
        - Future: use conversation history for better context
        """
        budget = budget or ContextBudget()
        context = RetrievedContext(
            retrieval_timestamp=datetime.utcnow().isoformat(),
            memory_query_used=query[:100] if query else None
        )

        # 1. Load core identity (cached after first load)
        context.core_identity = await self._get_core_identity()

        # 2. Load traits (always, they're small)
        context.traits = await self._get_traits()

        # 3. Retrieve relevant memories using embeddings
        # ITERATION NOTE: This is the key area for improvement
        if query:
            memories, considered = await self._get_relevant_memories(
                query=query,
                limit=memory_limit
            )
            context.memories = memories
            context.memories_considered = considered

        # 4. Load preferences by category
        categories = preference_categories or ['communication', 'general']
        context.preferences = await self._get_preferences(categories)

        # 5. Add project context if provided
        context.project_context = project_context

        # 6. Load user context
        context.user_context = await self._get_user_context()

        return context

    async def _get_core_identity(self) -> Dict[str, Any]:
        """
        Get core persona identity.

        Cached because it rarely changes.

        ITERATION NOTE: Add cache invalidation on persona updates
        """
        if self._core_identity_cache:
            return self._core_identity_cache

        query = """
        MATCH (p:Persona)
        RETURN p, elementId(p) as id
        LIMIT 1
        """

        with self.graph.session() as session:
            result = session.run(query)
            record = result.single()
            if record and record["p"]:
                data = dict(record["p"])
                data["id"] = record["id"]
                self._persona_id = record["id"]
                self._core_identity_cache = data
                return data

        return {}

    async def _get_traits(self) -> List[Dict[str, Any]]:
        """
        Get persona traits.

        ITERATION NOTE:
        - Currently loads all traits
        - Future: prioritize by strength, filter by context
        """
        if not self._persona_id:
            await self._get_core_identity()

        if not self._persona_id:
            return []

        query = """
        MATCH (p:Persona)-[:HAS_TRAIT]->(t:Trait)
        WHERE elementId(p) = $persona_id
        RETURN t
        ORDER BY t.strength DESC
        LIMIT 10
        """

        traits = []
        with self.graph.session() as session:
            result = session.run(query, persona_id=self._persona_id)
            for record in result:
                traits.append(dict(record["t"]))

        return traits

    async def _get_relevant_memories(
        self,
        query: str,
        limit: int = 5
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Retrieve memories relevant to the query using embedding similarity.

        Args:
            query: User message to match against
            limit: Max memories to return

        Returns:
            Tuple of (memories, total_considered)

        ITERATION NOTE: This is the MOST IMPORTANT function to iterate on.
        Current implementation is basic cosine similarity.

        Future improvements:
        - Hybrid search (combine embedding + keyword)
        - Temporal weighting (recent memories score higher)
        - Usage tracking (frequently helpful memories score higher)
        - Entity extraction (if query mentions "mom", find family memories)
        - Contextual boosting (work context boosts work memories)
        - Memory importance scores
        - Conversation-aware retrieval
        """
        if not self._persona_id:
            await self._get_core_identity()

        if not self._persona_id:
            return [], 0

        # Get query embedding
        try:
            query_embedding = await self.embedder.embed(query)
        except Exception as e:
            # ITERATION NOTE: Better error handling needed
            print(f"Embedding failed: {e}")
            return await self._get_recent_memories(limit), 0

        # Check if we have vector index
        # ITERATION NOTE: Should cache whether index exists
        try:
            # Try vector search first
            memories, total = await self._vector_search_memories(
                query_embedding,
                limit
            )
            if memories:
                return memories, total
        except Exception as e:
            # Vector index might not exist, fall back to loading all and computing
            print(f"Vector search failed, using fallback: {e}")

        # Fallback: Load memories and compute similarity in Python
        # ITERATION NOTE: This is inefficient, but works without vector index
        return await self._fallback_memory_search(query_embedding, limit)

    async def _vector_search_memories(
        self,
        embedding: List[float],
        limit: int
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Search memories using Neo4j vector index.

        Requires vector index on Memory.embedding

        ITERATION NOTE:
        - Need to ensure memories have embeddings when created
        - Consider hybrid search combining vector + text
        """
        query = """
        MATCH (p:Persona)-[:HAS_MEMORY]->(m:Memory)
        WHERE elementId(p) = $persona_id AND m.embedding IS NOT NULL
        WITH m, gds.similarity.cosine(m.embedding, $embedding) AS score
        WHERE score > 0.5
        RETURN m, score
        ORDER BY score DESC
        LIMIT $limit
        """

        memories = []
        with self.graph.session() as session:
            result = session.run(
                query,
                persona_id=self._persona_id,
                embedding=embedding,
                limit=limit
            )
            for record in result:
                mem = dict(record["m"])
                mem["_relevance_score"] = record["score"]
                memories.append(mem)

        # Get total count
        count_query = """
        MATCH (p:Persona)-[:HAS_MEMORY]->(m:Memory)
        WHERE elementId(p) = $persona_id
        RETURN count(m) as total
        """
        with self.graph.session() as session:
            result = session.run(count_query, persona_id=self._persona_id)
            total = result.single()["total"]

        return memories, total

    async def _fallback_memory_search(
        self,
        query_embedding: List[float],
        limit: int
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Fallback memory search when vector index unavailable.

        Loads all memories and computes similarity in Python.

        ITERATION NOTE:
        - This is O(n) and won't scale
        - Need to create vector index or use external vector DB
        - Consider caching memory embeddings
        """
        import numpy as np

        query = """
        MATCH (p:Persona)-[:HAS_MEMORY]->(m:Memory)
        WHERE elementId(p) = $persona_id
        RETURN m, elementId(m) as id
        """

        memories = []
        with self.graph.session() as session:
            result = session.run(query, persona_id=self._persona_id)
            for record in result:
                mem = dict(record["m"])
                mem["id"] = record["id"]
                memories.append(mem)

        total = len(memories)

        if not memories:
            return [], 0

        # Compute embeddings for memories that don't have them
        # ITERATION NOTE: Should pre-compute and store these
        memories_with_scores = []
        query_vec = np.array(query_embedding)

        for mem in memories:
            if mem.get("embedding"):
                mem_vec = np.array(mem["embedding"])
                # Cosine similarity
                score = np.dot(query_vec, mem_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(mem_vec)
                )
                mem["_relevance_score"] = float(score)
                memories_with_scores.append(mem)
            else:
                # No embedding, compute one
                # ITERATION NOTE: Should batch these and store
                try:
                    content = mem.get("content", mem.get("name", ""))
                    mem_embedding = await self.embedder.embed(content)
                    mem_vec = np.array(mem_embedding)
                    score = np.dot(query_vec, mem_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(mem_vec)
                    )
                    mem["_relevance_score"] = float(score)
                    memories_with_scores.append(mem)

                    # Store embedding for future use
                    # ITERATION NOTE: Do this async in background
                    await self._store_memory_embedding(mem["id"], mem_embedding)
                except Exception as e:
                    print(f"Failed to embed memory: {e}")
                    mem["_relevance_score"] = 0.0
                    memories_with_scores.append(mem)

        # Sort by score and take top-k
        memories_with_scores.sort(key=lambda x: x.get("_relevance_score", 0), reverse=True)

        return memories_with_scores[:limit], total

    async def _store_memory_embedding(self, memory_id: str, embedding: List[float]):
        """
        Store computed embedding back to memory node.

        ITERATION NOTE:
        - Should do this in background
        - Should batch multiple updates
        """
        query = """
        MATCH (m:Memory) WHERE elementId(m) = $id
        SET m.embedding = $embedding
        """
        try:
            with self.graph.session() as session:
                session.run(query, id=memory_id, embedding=embedding)
        except Exception as e:
            print(f"Failed to store embedding: {e}")

    async def _get_recent_memories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get most recent memories as fallback.

        Used when embedding retrieval fails.
        """
        if not self._persona_id:
            return []

        query = """
        MATCH (p:Persona)-[:HAS_MEMORY]->(m:Memory)
        WHERE elementId(p) = $persona_id
        RETURN m
        ORDER BY m.created_at DESC
        LIMIT $limit
        """

        memories = []
        with self.graph.session() as session:
            result = session.run(query, persona_id=self._persona_id, limit=limit)
            for record in result:
                memories.append(dict(record["m"]))

        return memories

    async def _get_preferences(
        self,
        categories: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get preferences by category.

        ITERATION NOTE:
        - Add confidence threshold filtering
        - Add preference staleness detection
        - Consider preference conflicts
        """
        if not self._persona_id:
            return []

        query = """
        MATCH (p:Persona)-[:LEARNED_PREFERENCE]->(pref:Preference)
        WHERE elementId(p) = $persona_id
        AND pref.category IN $categories
        RETURN pref
        ORDER BY pref.confidence DESC
        LIMIT 10
        """

        preferences = []
        with self.graph.session() as session:
            result = session.run(
                query,
                persona_id=self._persona_id,
                categories=categories
            )
            for record in result:
                preferences.append(dict(record["pref"]))

        return preferences

    async def _get_user_context(self) -> Optional[Dict[str, Any]]:
        """
        Get user information for context.

        ITERATION NOTE:
        - Cache user info
        - Add user preference summary
        """
        query = """
        MATCH (u:User)
        RETURN u, elementId(u) as id
        LIMIT 1
        """

        with self.graph.session() as session:
            result = session.run(query)
            record = result.single()
            if record and record["u"]:
                data = dict(record["u"])
                data["id"] = record["id"]
                return data

        return None

    def invalidate_cache(self):
        """
        Clear cached context.

        Call this after persona updates.
        """
        self._core_identity_cache = None
        self._persona_id = None


# Singleton instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get singleton ContextManager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
