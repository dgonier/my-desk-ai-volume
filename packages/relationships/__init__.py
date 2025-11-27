"""
Relationships Package

This package manages identity and relationship information for the cognitive tree.
It stores "who" the agent knows about and their personal context.

Key concepts from cognitive-tree.md:
- Identity = accumulated transition distribution (how the agent engages with entities)
- Relationships = joint chains / chain entanglement between entities
- Every interaction is both query AND creation

This package provides the foundational data layer for:
- User profiles (name, location, preferences)
- Relationship tracking (interaction history, context)
- Entity management (people, organizations, etc.)
"""

from .models import (
    UserProfile,
    Location,
    ContactInfo,
    Preferences,
    Entity,
    Relationship,
    InteractionRecord,
)
from .store import RelationshipStore, get_store
from .default_profile import ensure_profile_exists, create_default_profile

__all__ = [
    "UserProfile",
    "Location",
    "ContactInfo",
    "Preferences",
    "Entity",
    "Relationship",
    "InteractionRecord",
    "RelationshipStore",
    "get_store",
    "ensure_profile_exists",
    "create_default_profile",
]
