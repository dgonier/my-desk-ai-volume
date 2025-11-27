
"""
Pydantic models for relationships and identity management.

These models define the structure for storing information about:
- The primary user (owner of the agent)
- Other entities the agent interacts with
- Relationships between entities
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class EntityType(str, Enum):
    """Types of entities the agent can track."""
    USER = "user"           # The primary user (owner)
    PERSON = "person"       # Other people
    ORGANIZATION = "org"    # Companies, groups
    PLACE = "place"         # Locations, venues
    PROJECT = "project"     # Work projects, initiatives


class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    OWNER = "owner"         # Primary user relationship
    FAMILY = "family"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    EMPLOYER = "employer"
    CLIENT = "client"
    ACQUAINTANCE = "acquaintance"


class Location(BaseModel):
    """Geographic location information."""
    city: str
    state: Optional[str] = None
    country: str = "USA"
    zip_code: Optional[str] = None
    timezone: Optional[str] = None

    # For job searches, commute calculations, etc.
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def __str__(self) -> str:
        parts = [self.city]
        if self.state:
            parts.append(self.state)
        if self.country != "USA":
            parts.append(self.country)
        return ", ".join(parts)

    @property
    def search_string(self) -> str:
        """Format suitable for job searches, API queries, etc."""
        if self.state:
            return f"{self.city}, {self.state}"
        return f"{self.city}, {self.country}"


class ContactInfo(BaseModel):
    """Contact information for an entity."""
    email: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    twitter: Optional[str] = None
    website: Optional[str] = None


class Preferences(BaseModel):
    """User preferences that affect agent behavior."""
    # Communication preferences
    preferred_name: Optional[str] = None
    communication_style: str = "professional"  # casual, professional, formal

    # Job search preferences
    job_titles: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    salary_minimum: Optional[int] = None
    remote_preference: str = "flexible"  # remote, hybrid, onsite, flexible
    willing_to_relocate: bool = False

    # General preferences
    interests: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)

    # Agent behavior
    notification_frequency: str = "daily"  # realtime, daily, weekly
    language: str = "en"


class UserProfile(BaseModel):
    """
    The primary user profile - the owner of this agent instance.

    This is the core identity that the agent serves. There should only be
    one UserProfile per agent instance.
    """
    id: str = "primary_user"

    # Basic identity
    first_name: str
    last_name: Optional[str] = None
    nickname: Optional[str] = None

    # Location (critical for personalization)
    location: Location

    # Contact
    contact: ContactInfo = Field(default_factory=ContactInfo)

    # Preferences
    preferences: Preferences = Field(default_factory=Preferences)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Extensible attributes
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """Get the preferred display name."""
        if self.preferences.preferred_name:
            return self.preferences.preferred_name
        if self.nickname:
            return self.nickname
        return self.first_name

    @property
    def full_name(self) -> str:
        """Get the full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name


class Entity(BaseModel):
    """
    A generic entity that the agent knows about.

    Entities can be people, organizations, places, or projects.
    The UserProfile is a special case of Entity with type=USER.
    """
    id: str
    type: EntityType
    name: str
    description: Optional[str] = None

    # Optional location
    location: Optional[Location] = None

    # Contact info (for people/orgs)
    contact: Optional[ContactInfo] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Extensible attributes
    attributes: Dict[str, Any] = Field(default_factory=dict)


class InteractionRecord(BaseModel):
    """
    Record of an interaction with an entity.

    This feeds into the cognitive tree's Markov chain tracking -
    what patterns emerge when engaging with this entity.
    """
    id: str
    entity_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Interaction details
    channel: str  # whatsapp, terminal, api, etc.
    summary: str

    # Cognitive moves made (connects to cognitive tree)
    cognitive_moves: List[str] = Field(default_factory=list)

    # Outcome tracking
    outcome: Optional[str] = None  # positive, negative, neutral
    value: float = 0.0  # For backpropagation in cognitive tree

    # Context
    context: Dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    """
    A relationship between the user and an entity.

    This maps to the "joint trees" concept from cognitive-tree.md -
    tracking collaborative patterns and entanglement between chains.
    """
    id: str
    entity_id: str
    relationship_type: RelationshipType

    # Relationship metadata
    since: Optional[datetime] = None
    strength: float = 0.5  # 0.0 to 1.0, tracks relationship strength

    # Interaction stats (for cognitive tree)
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None

    # Joint patterns that have emerged
    shared_contexts: List[str] = Field(default_factory=list)

    # Notes
    notes: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
