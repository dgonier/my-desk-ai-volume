"""
RelationshipStore - Persistence layer for relationships data.

Stores data as JSON files in the data directory, designed to work
with Modal's volume persistence.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .models import (
    UserProfile,
    Location,
    ContactInfo,
    Preferences,
    Entity,
    Relationship,
    InteractionRecord,
)


class RelationshipStore:
    """
    File-based storage for relationships data.

    Data is stored in JSON files under the specified data directory:
    - profile.json - The primary user profile
    - entities.json - Other entities
    - relationships.json - Relationships between user and entities
    - interactions/ - Interaction records (one file per entity)
    """

    def __init__(self, data_dir: str = "/home/claude/data/relationships"):
        self.data_dir = Path(data_dir)
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "interactions").mkdir(exist_ok=True)

    def _read_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Read a JSON file, returning None if it doesn't exist."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return None
        with open(filepath, "r") as f:
            return json.load(f)

    def _write_json(self, filename: str, data: Dict[str, Any]):
        """Write data to a JSON file."""
        filepath = self.data_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # ==================== User Profile ====================

    def get_user_profile(self) -> Optional[UserProfile]:
        """Get the primary user profile."""
        data = self._read_json("profile.json")
        if data is None:
            return None
        return UserProfile(**data)

    def save_user_profile(self, profile: UserProfile) -> UserProfile:
        """Save the primary user profile."""
        profile.updated_at = datetime.utcnow()
        self._write_json("profile.json", profile.model_dump())
        return profile

    def update_user_profile(self, **kwargs) -> Optional[UserProfile]:
        """Update specific fields of the user profile."""
        profile = self.get_user_profile()
        if profile is None:
            return None

        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        return self.save_user_profile(profile)

    # ==================== Entities ====================

    def get_entities(self) -> List[Entity]:
        """Get all entities."""
        data = self._read_json("entities.json")
        if data is None:
            return []
        return [Entity(**e) for e in data.get("entities", [])]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get a specific entity by ID."""
        entities = self.get_entities()
        for entity in entities:
            if entity.id == entity_id:
                return entity
        return None

    def save_entity(self, entity: Entity) -> Entity:
        """Save or update an entity."""
        entities = self.get_entities()

        # Update existing or add new
        updated = False
        for i, e in enumerate(entities):
            if e.id == entity.id:
                entity.updated_at = datetime.utcnow()
                entities[i] = entity
                updated = True
                break

        if not updated:
            entities.append(entity)

        self._write_json("entities.json", {
            "entities": [e.model_dump() for e in entities]
        })
        return entity

    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity."""
        entities = self.get_entities()
        original_count = len(entities)
        entities = [e for e in entities if e.id != entity_id]

        if len(entities) < original_count:
            self._write_json("entities.json", {
                "entities": [e.model_dump() for e in entities]
            })
            return True
        return False

    # ==================== Relationships ====================

    def get_relationships(self) -> List[Relationship]:
        """Get all relationships."""
        data = self._read_json("relationships.json")
        if data is None:
            return []
        return [Relationship(**r) for r in data.get("relationships", [])]

    def get_relationship(self, entity_id: str) -> Optional[Relationship]:
        """Get relationship with a specific entity."""
        relationships = self.get_relationships()
        for rel in relationships:
            if rel.entity_id == entity_id:
                return rel
        return None

    def save_relationship(self, relationship: Relationship) -> Relationship:
        """Save or update a relationship."""
        relationships = self.get_relationships()

        updated = False
        for i, r in enumerate(relationships):
            if r.id == relationship.id:
                relationship.updated_at = datetime.utcnow()
                relationships[i] = relationship
                updated = True
                break

        if not updated:
            relationships.append(relationship)

        self._write_json("relationships.json", {
            "relationships": [r.model_dump() for r in relationships]
        })
        return relationship

    # ==================== Interactions ====================

    def log_interaction(self, record: InteractionRecord) -> InteractionRecord:
        """Log an interaction with an entity."""
        filename = f"interactions/{record.entity_id}.json"
        data = self._read_json(filename) or {"interactions": []}

        data["interactions"].append(record.model_dump())

        # Keep only last 1000 interactions per entity
        if len(data["interactions"]) > 1000:
            data["interactions"] = data["interactions"][-1000:]

        self._write_json(filename, data)

        # Update relationship stats
        rel = self.get_relationship(record.entity_id)
        if rel:
            rel.interaction_count += 1
            rel.last_interaction = record.timestamp
            self.save_relationship(rel)

        return record

    def get_interactions(
        self,
        entity_id: str,
        limit: int = 100
    ) -> List[InteractionRecord]:
        """Get recent interactions with an entity."""
        filename = f"interactions/{entity_id}.json"
        data = self._read_json(filename)
        if data is None:
            return []

        records = [InteractionRecord(**r) for r in data.get("interactions", [])]
        return records[-limit:]

    # ==================== Convenience Methods ====================

    def get_user_location(self) -> Optional[Location]:
        """Get just the user's location."""
        profile = self.get_user_profile()
        if profile:
            return profile.location
        return None

    def get_user_job_preferences(self) -> Dict[str, Any]:
        """Get user's job search preferences."""
        profile = self.get_user_profile()
        if not profile:
            return {}

        prefs = profile.preferences
        return {
            "location": profile.location.search_string,
            "titles": prefs.job_titles,
            "industries": prefs.industries,
            "salary_minimum": prefs.salary_minimum,
            "remote_preference": prefs.remote_preference,
            "willing_to_relocate": prefs.willing_to_relocate,
        }


# Singleton instance for easy access
_store: Optional[RelationshipStore] = None


def get_store(data_dir: str = "/home/claude/data/relationships") -> RelationshipStore:
    """Get or create the singleton store instance."""
    global _store
    if _store is None:
        _store = RelationshipStore(data_dir)
    return _store
