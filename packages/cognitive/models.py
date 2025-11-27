"""
Core models for the cognitive graph.

These define the node and relationship types used across all packages.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    """All node types in the cognitive graph."""
    # Core identity nodes (graph always starts with these)
    USER = "User"           # The human user
    ASSISTANT = "Assistant" # The AI assistant (legacy)
    PERSONA = "Persona"     # The Persona Agent's evolving identity

    # Relationships package
    PERSON = "Person"
    ORGANIZATION = "Organization"

    # Cycles and Projects (self-directed work)
    CYCLE = "Cycle"         # A self-assigned task toward a larger goal
    PROJECT = "Project"     # A larger endeavor (book, research project, etc.)
    CHAPTER = "Chapter"     # A section of a project
    DRAFT = "Draft"         # A version of content
    TASK = "Task"           # An actionable item within a cycle
    GOAL = "Goal"           # A high-level objective

    # Research package
    ARTICLE = "Article"
    JOB = "Job"
    TOPIC = "Topic"
    SOURCE = "Source"
    SCHOLARSHIP = "Scholarship"

    # Knowledge chunks (for RAG/vector search)
    CHUNK = "Chunk"         # A text chunk with embedding
    ENTITY = "Entity"       # An extracted entity
    DOCUMENT = "Document"   # A full document

    # Comms package
    CONVERSATION = "Conversation"
    MESSAGE = "Message"
    CALL = "Call"

    # Generic
    NOTE = "Note"
    TAG = "Tag"
    INSIGHT = "Insight"     # A learned insight or pattern

    # Persona Identity
    MEMORY = "Memory"       # Persona's constructed memories/stories
    TRAIT = "Trait"         # Personality traits
    PREFERENCE = "Preference"  # User preferences learned by persona


class RelationType(str, Enum):
    """All relationship types in the cognitive graph."""
    # Core identity relationships
    ASSISTS = "ASSISTS"             # Assistant -> User
    OWNS = "OWNS"                   # User -> Project/Cycle

    # Persona identity relationships
    HAS_TRAIT = "HAS_TRAIT"         # Persona -> Trait
    HAS_MEMORY = "HAS_MEMORY"       # Persona -> Memory
    LEARNED_PREFERENCE = "LEARNED_PREFERENCE"  # Persona -> Preference
    ADAPTED_FOR = "ADAPTED_FOR"     # Persona -> User (personalization)

    # Cycle and Project relationships
    INITIATED = "INITIATED"         # Assistant -> Cycle (agent-initiated work)
    PART_OF = "PART_OF"            # Task/Chapter -> Cycle/Project
    CONTAINS = "CONTAINS"          # Project -> Chapter, Cycle -> Task
    WORKS_TOWARD = "WORKS_TOWARD"  # Cycle -> Goal
    DEPENDS_ON = "DEPENDS_ON"      # Task -> Task
    DERIVED_FROM = "DERIVED_FROM"  # Draft -> Draft (versioning)
    INFORMS = "INFORMS"            # Insight -> Cycle/Project
    USES_SOURCE = "USES_SOURCE"    # Chapter/Draft -> Source/Article

    # Person relationships
    KNOWS = "KNOWS"
    WORKS_AT = "WORKS_AT"
    WORKED_AT = "WORKED_AT"
    LIVES_IN = "LIVES_IN"
    MEMBER_OF = "MEMBER_OF"          # Person -> Project (family member, team member)
    COLLABORATES_ON = "COLLABORATES_ON"  # Person -> Project (working together)

    # Research relationships
    RESEARCHED = "RESEARCHED"
    INTERESTED_IN = "INTERESTED_IN"
    APPLIED_TO = "APPLIED_TO"
    AUTHORED = "AUTHORED"
    PUBLISHED_BY = "PUBLISHED_BY"
    ABOUT_TOPIC = "ABOUT_TOPIC"
    RELATED_TO = "RELATED_TO"
    CITED_BY = "CITED_BY"

    # Job relationships
    POSTED_BY = "POSTED_BY"
    REQUIRES_SKILL = "REQUIRES_SKILL"
    LOCATED_IN = "LOCATED_IN"

    # Comms relationships
    PARTICIPATED_IN = "PARTICIPATED_IN"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    DISCUSSED = "DISCUSSED"
    MENTIONED = "MENTIONED"

    # Vector/RAG relationships
    HAS_CHUNK = "HAS_CHUNK"         # Document -> Chunk
    REFERENCES = "REFERENCES"       # Chunk -> Entity
    SIMILAR_TO = "SIMILAR_TO"       # Entity -> Entity (semantic similarity)

    # Generic
    TAGGED_WITH = "TAGGED_WITH"
    HAS_NOTE = "HAS_NOTE"


class Node(BaseModel):
    """Base model for all graph nodes."""
    id: Optional[str] = None  # Neo4j internal ID (set after creation)
    type: NodeType
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_cypher_props(self) -> Dict[str, Any]:
        """Convert to properties dict for Cypher query."""
        props = {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            **self.properties
        }
        return props


class Relationship(BaseModel):
    """Base model for graph relationships."""
    type: RelationType
    from_node_id: str
    to_node_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_cypher_props(self) -> Dict[str, Any]:
        """Convert to properties dict for Cypher query."""
        props = {
            "created_at": self.created_at.isoformat(),
            **self.properties
        }
        return props


# Specific node models with typed properties

class UserNode(Node):
    """The primary user of the system."""
    type: NodeType = NodeType.USER

    @classmethod
    def create(
        cls,
        first_name: str,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: str = "USA",
        job_titles: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        **kwargs
    ) -> "UserNode":
        name = f"{first_name} {last_name}" if last_name else first_name
        return cls(
            name=name,
            properties={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "city": city,
                "state": state,
                "country": country,
                "job_titles": job_titles or [],
                "skills": skills or [],
                **kwargs
            }
        )


class ArticleNode(Node):
    """A research article or news item."""
    type: NodeType = NodeType.ARTICLE

    @classmethod
    def create(
        cls,
        title: str,
        url: str,
        summary: Optional[str] = None,
        author: Optional[str] = None,
        published_date: Optional[datetime] = None,
        source: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> "ArticleNode":
        return cls(
            name=title,
            properties={
                "url": url,
                "summary": summary,
                "author": author,
                "published_date": published_date.isoformat() if published_date else None,
                "source": source,
                "content": content,
                **kwargs
            }
        )


class JobNode(Node):
    """A job posting."""
    type: NodeType = NodeType.JOB

    @classmethod
    def create(
        cls,
        title: str,
        company: str,
        location: Optional[str] = None,
        salary: Optional[str] = None,
        url: Optional[str] = None,
        description: Optional[str] = None,
        job_type: Optional[str] = None,  # remote, hybrid, onsite
        level: Optional[str] = None,  # entry, mid, senior
        posted_date: Optional[datetime] = None,
        **kwargs
    ) -> "JobNode":
        return cls(
            name=f"{title} at {company}",
            properties={
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "url": url,
                "description": description,
                "job_type": job_type,
                "level": level,
                "posted_date": posted_date.isoformat() if posted_date else None,
                **kwargs
            }
        )


class TopicNode(Node):
    """A topic or concept (for knowledge graph)."""
    type: NodeType = NodeType.TOPIC

    @classmethod
    def create(
        cls,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        **kwargs
    ) -> "TopicNode":
        return cls(
            name=name,
            properties={
                "description": description,
                "category": category,
                **kwargs
            }
        )


class ConversationNode(Node):
    """A conversation (WhatsApp, call, etc.)."""
    type: NodeType = NodeType.CONVERSATION

    @classmethod
    def create(
        cls,
        channel: str,  # whatsapp, voice, sms
        participant: str,
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
        summary: Optional[str] = None,
        **kwargs
    ) -> "ConversationNode":
        started = started_at or datetime.utcnow()
        return cls(
            name=f"{channel} with {participant} at {started.isoformat()}",
            properties={
                "channel": channel,
                "participant": participant,
                "started_at": started.isoformat(),
                "ended_at": ended_at.isoformat() if ended_at else None,
                "summary": summary,
                **kwargs
            }
        )


# ============================================
# Core Identity Nodes
# ============================================

class AssistantNode(Node):
    """The AI assistant in the cognitive graph."""
    type: NodeType = NodeType.ASSISTANT

    @classmethod
    def create(
        cls,
        name: str = "Claude",
        model: str = "claude-sonnet-4-5-20250929",
        capabilities: Optional[List[str]] = None,
        **kwargs
    ) -> "AssistantNode":
        return cls(
            name=name,
            properties={
                "model": model,
                "capabilities": capabilities or [
                    "research", "writing", "analysis",
                    "coding", "conversation", "planning"
                ],
                **kwargs
            }
        )


# ============================================
# Cycle and Project Nodes
# ============================================

class CycleStatus(str, Enum):
    """Status of a cycle."""
    PLANNING = "planning"       # Cycle is being planned
    ACTIVE = "active"           # Cycle is in progress
    PAUSED = "paused"           # Temporarily paused
    COMPLETED = "completed"     # Successfully completed
    ABANDONED = "abandoned"     # Abandoned (with reason)


class CycleType(str, Enum):
    """Type of cycle."""
    RESEARCH = "research"           # Information gathering and synthesis
    INTROSPECTION = "introspection" # Self-reflection, understanding user
    PROJECT_WORK = "project_work"   # Working on a specific project
    MAINTENANCE = "maintenance"     # Graph maintenance, organization
    LEARNING = "learning"           # Learning about a new domain
    OUTREACH = "outreach"           # Reaching out, networking


class CycleNode(Node):
    """
    A Cycle is a self-assigned task toward a larger goal.

    Cycles are how the assistant organizes autonomous work. They have:
    - A clear objective
    - Tasks to complete
    - Sources/references gathered
    - Insights generated
    - Connection to larger goals/projects
    """
    type: NodeType = NodeType.CYCLE

    @classmethod
    def create(
        cls,
        name: str,
        objective: str,
        cycle_type: CycleType = CycleType.RESEARCH,
        status: CycleStatus = CycleStatus.PLANNING,
        priority: int = 5,  # 1-10, higher = more important
        estimated_tasks: Optional[int] = None,
        context: Optional[str] = None,  # Why this cycle was initiated
        **kwargs
    ) -> "CycleNode":
        return cls(
            name=name,
            properties={
                "objective": objective,
                "cycle_type": cycle_type.value,
                "status": status.value,
                "priority": priority,
                "estimated_tasks": estimated_tasks,
                "context": context,
                "tasks_completed": 0,
                "insights_count": 0,
                **kwargs
            }
        )


class ProjectCategory(str, Enum):
    """Categories for projects - both work and life areas."""
    # Work/Professional
    WORK = "work"               # General work projects
    BOOK = "book"               # Writing a book
    RESEARCH = "research"       # Research project
    CAMPAIGN = "campaign"       # Job search, marketing, etc.
    LEARNING = "learning"       # Learning a new skill/domain

    # Life Areas
    FAMILY = "family"           # Family-related (spouse, kids, parents)
    HEALTH = "health"           # Health & fitness
    FINANCE = "finance"         # Financial goals
    SOCIAL = "social"           # Friendships, community
    HOBBY = "hobby"             # Hobbies, creative pursuits
    TRAVEL = "travel"           # Travel plans
    HOME = "home"               # Home improvement, maintenance

    # Meta
    GENERAL = "general"         # Uncategorized


class ProjectNode(Node):
    """
    A Project is a larger endeavor that may span multiple cycles.

    Projects can be:
    - Work projects: Books, research papers, job searches, campaigns
    - Life areas: Family, Health, Finance, Social, Hobbies

    Projects can have:
    - People associated via MEMBER_OF or COLLABORATES_ON relationships
    - Articles/resources associated via USES_SOURCE relationship
    - Cycles (work sessions) that contribute to the project
    - Chapters/sections for structured content

    Examples:
    - "Write AI Book" (category: book)
    - "Family" (category: family) - links to spouse, kids, parents
    - "Health Goals 2024" (category: health) - links to health articles, doctor contacts
    - "Job Search" (category: campaign) - links to recruiters, job postings
    """
    type: NodeType = NodeType.PROJECT

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        category: ProjectCategory = ProjectCategory.GENERAL,
        project_type: Optional[str] = None,  # More specific type within category
        status: str = "active",
        is_life_area: bool = False,  # True for permanent life areas (Family, Health)
        **kwargs
    ) -> "ProjectNode":
        return cls(
            name=name,
            properties={
                "description": description,
                "category": category.value if isinstance(category, ProjectCategory) else category,
                "project_type": project_type,
                "status": status,
                "is_life_area": is_life_area,
                **kwargs
            }
        )

    @classmethod
    def create_life_area(
        cls,
        name: str,
        category: ProjectCategory,
        description: Optional[str] = None,
        **kwargs
    ) -> "ProjectNode":
        """
        Create a permanent life area project.

        Life areas are always-active projects that represent ongoing
        areas of focus (Family, Health, Finance, etc.)
        """
        default_descriptions = {
            ProjectCategory.FAMILY: "Family relationships and activities",
            ProjectCategory.HEALTH: "Health, fitness, and wellness",
            ProjectCategory.FINANCE: "Financial planning and goals",
            ProjectCategory.SOCIAL: "Friendships and community",
            ProjectCategory.HOBBY: "Hobbies and creative pursuits",
            ProjectCategory.LEARNING: "Learning and personal development",
            ProjectCategory.WORK: "Professional career and work",
            ProjectCategory.HOME: "Home and living space",
        }
        return cls.create(
            name=name,
            description=description or default_descriptions.get(category, f"{name} life area"),
            category=category,
            status="active",
            is_life_area=True,
            **kwargs
        )


class ChapterNode(Node):
    """A chapter or section within a project."""
    type: NodeType = NodeType.CHAPTER

    @classmethod
    def create(
        cls,
        title: str,
        order: int,
        description: Optional[str] = None,
        status: str = "outline",  # outline, draft, review, final
        **kwargs
    ) -> "ChapterNode":
        return cls(
            name=title,
            properties={
                "title": title,
                "order": order,
                "description": description,
                "status": status,
                **kwargs
            }
        )


class DraftNode(Node):
    """A draft version of content."""
    type: NodeType = NodeType.DRAFT

    @classmethod
    def create(
        cls,
        title: str,
        content: str,
        version: int = 1,
        word_count: Optional[int] = None,
        **kwargs
    ) -> "DraftNode":
        return cls(
            name=f"{title} v{version}",
            properties={
                "title": title,
                "content": content,
                "version": version,
                "word_count": word_count or len(content.split()),
                **kwargs
            }
        )


class TaskNode(Node):
    """An actionable task within a cycle."""
    type: NodeType = NodeType.TASK

    @classmethod
    def create(
        cls,
        description: str,
        status: str = "pending",  # pending, in_progress, completed, blocked
        priority: int = 5,
        estimated_minutes: Optional[int] = None,
        **kwargs
    ) -> "TaskNode":
        return cls(
            name=description[:100],  # Truncate for name
            properties={
                "description": description,
                "status": status,
                "priority": priority,
                "estimated_minutes": estimated_minutes,
                **kwargs
            }
        )


class GoalNode(Node):
    """A high-level objective that cycles work toward."""
    type: NodeType = NodeType.GOAL

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        timeframe: Optional[str] = None,  # short-term, medium-term, long-term
        success_criteria: Optional[List[str]] = None,
        **kwargs
    ) -> "GoalNode":
        return cls(
            name=name,
            properties={
                "description": description,
                "timeframe": timeframe,
                "success_criteria": success_criteria or [],
                **kwargs
            }
        )


class InsightNode(Node):
    """A learned insight or pattern."""
    type: NodeType = NodeType.INSIGHT

    @classmethod
    def create(
        cls,
        insight: str,
        source_type: str,  # research, conversation, introspection
        confidence: float = 0.7,  # 0-1
        **kwargs
    ) -> "InsightNode":
        return cls(
            name=insight[:100],
            properties={
                "insight": insight,
                "source_type": source_type,
                "confidence": confidence,
                **kwargs
            }
        )


# ============================================
# Vector/RAG Nodes
# ============================================

class ChunkNode(Node):
    """A text chunk with embedding for vector search."""
    type: NodeType = NodeType.CHUNK

    @classmethod
    def create(
        cls,
        text: str,
        embedding: Optional[List[float]] = None,
        source_id: Optional[str] = None,
        chunk_index: int = 0,
        **kwargs
    ) -> "ChunkNode":
        return cls(
            name=text[:50] + "..." if len(text) > 50 else text,
            properties={
                "text": text,
                "embedding": embedding,  # Will be set by embedding service
                "source_id": source_id,
                "chunk_index": chunk_index,
                "char_count": len(text),
                **kwargs
            }
        )


class EntityNode(Node):
    """An extracted entity with optional embedding."""
    type: NodeType = NodeType.ENTITY

    @classmethod
    def create(
        cls,
        name: str,
        entity_type: str,  # person, organization, concept, location, etc.
        description: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        **kwargs
    ) -> "EntityNode":
        return cls(
            name=name,
            properties={
                "entity_type": entity_type,
                "description": description,
                "embedding": embedding,
                **kwargs
            }
        )


class DocumentNode(Node):
    """A full document that gets chunked for RAG."""
    type: NodeType = NodeType.DOCUMENT

    @classmethod
    def create(
        cls,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        doc_type: Optional[str] = None,  # article, pdf, webpage, etc.
        **kwargs
    ) -> "DocumentNode":
        return cls(
            name=title,
            properties={
                "title": title,
                "content": content,
                "source_url": source_url,
                "doc_type": doc_type,
                "char_count": len(content),
                "word_count": len(content.split()),
                **kwargs
            }
        )


# ============================================
# Persona Identity Nodes
# ============================================

class PersonaNode(Node):
    """
    The Persona Agent's evolving identity.

    Unlike a static assistant, the Persona:
    - Has a self-chosen name
    - Constructs its own personality traits
    - Creates backstory/memories for relatability
    - Adapts communication style to user preferences
    - Stores voice description for TTS consistency

    The persona evolves through persona-cycles where it:
    - Reflects on conversations to refine personality
    - Creates anecdotes and stories
    - Adjusts traits based on user feedback
    - Develops deeper understanding of user
    """
    type: NodeType = NodeType.PERSONA

    @classmethod
    def create(
        cls,
        name: str,
        tagline: Optional[str] = None,
        personality_summary: Optional[str] = None,
        voice_description: Optional[str] = None,
        communication_style: Optional[str] = None,
        core_values: Optional[List[str]] = None,
        interests: Optional[List[str]] = None,
        quirks: Optional[List[str]] = None,
        avatar_description: Optional[str] = None,
        model: str = "anthropic.claude-sonnet-4-5-20250929-v1:0",
        initialization_complete: bool = False,
        **kwargs
    ) -> "PersonaNode":
        return cls(
            name=name,
            properties={
                "tagline": tagline,  # Short intro like "Your thoughtful companion"
                "personality_summary": personality_summary,
                "voice_description": voice_description,  # For TTS: "warm, calm, slightly playful"
                "communication_style": communication_style,  # "conversational", "formal", etc.
                "core_values": core_values or [],
                "interests": interests or [],
                "quirks": quirks or [],  # Small personality touches
                "avatar_description": avatar_description,
                "model": model,
                "initialization_complete": initialization_complete,
                "conversation_count": 0,
                "last_persona_cycle": None,
                **kwargs
            }
        )


class TraitNode(Node):
    """
    A personality trait of the Persona.

    Traits are characteristics that define how the persona
    behaves and communicates. They can be:
    - Core traits (fundamental, rarely change)
    - Adaptive traits (adjust based on user preferences)
    - Contextual traits (activate in specific situations)
    """
    type: NodeType = NodeType.TRAIT

    @classmethod
    def create(
        cls,
        trait_name: str,
        description: str,
        trait_type: str = "core",  # core, adaptive, contextual
        strength: float = 0.7,  # 0-1, how prominent this trait is
        examples: Optional[List[str]] = None,  # Example behaviors
        triggers: Optional[List[str]] = None,  # When this trait activates (for contextual)
        **kwargs
    ) -> "TraitNode":
        return cls(
            name=trait_name,
            properties={
                "description": description,
                "trait_type": trait_type,
                "strength": strength,
                "examples": examples or [],
                "triggers": triggers or [],
                **kwargs
            }
        )


class MemoryNode(Node):
    """
    A constructed memory or story for the Persona.

    Memories make the persona relatable and give it depth.
    They can be:
    - Anecdotes: Short stories to illustrate points
    - Preferences: "I've always found that..."
    - Experiences: Simulated past experiences
    - Observations: Things the persona has "noticed"

    These are constructed, not real, but help create
    a consistent and engaging personality.
    """
    type: NodeType = NodeType.MEMORY

    @classmethod
    def create(
        cls,
        title: str,
        content: str,
        memory_type: str = "anecdote",  # anecdote, preference, experience, observation
        emotional_tone: Optional[str] = None,  # warm, humorous, thoughtful, etc.
        use_contexts: Optional[List[str]] = None,  # When to bring up this memory
        related_topics: Optional[List[str]] = None,
        **kwargs
    ) -> "MemoryNode":
        return cls(
            name=title,
            properties={
                "content": content,
                "memory_type": memory_type,
                "emotional_tone": emotional_tone,
                "use_contexts": use_contexts or [],
                "related_topics": related_topics or [],
                "times_used": 0,
                **kwargs
            }
        )


class PreferenceNode(Node):
    """
    A learned user preference.

    The Persona learns and stores user preferences to
    personalize interactions:
    - Communication preferences (formal/casual, detailed/brief)
    - Topic interests
    - Scheduling preferences
    - Interaction patterns
    """
    type: NodeType = NodeType.PREFERENCE

    @classmethod
    def create(
        cls,
        preference_name: str,
        value: Any,
        category: str = "general",  # communication, topic, scheduling, interaction
        confidence: float = 0.5,  # 0-1, how confident in this preference
        source: str = "inferred",  # explicit, inferred, observed
        last_confirmed: Optional[str] = None,
        **kwargs
    ) -> "PreferenceNode":
        return cls(
            name=preference_name,
            properties={
                "value": value,
                "category": category,
                "confidence": confidence,
                "source": source,
                "last_confirmed": last_confirmed,
                "observation_count": 1,
                **kwargs
            }
        )
