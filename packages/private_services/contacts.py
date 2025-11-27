"""
Contact Management with Neo4j Integration

Automatically tracks contacts discovered from emails and other services.
Stores relationship information in the cognitive graph.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime


# Add packages to path for cognitive import
sys.path.insert(0, '/packages')


class ContactManager:
    """
    Manages contacts in the Neo4j cognitive graph.

    When the agent reads emails or accesses other services, contacts
    are automatically extracted and stored with context about how
    they were discovered.

    Contact nodes have:
    - name: Display name
    - email: Primary email address
    - relationship: How they relate to the user (colleague, friend, recruiter, etc.)
    - context: How they were discovered
    - first_seen: When first encountered
    - last_interaction: Last email/interaction date
    - interaction_count: Number of interactions
    """

    def __init__(self):
        try:
            from cognitive import get_graph
            self.graph = get_graph()
            self._connected = True
        except Exception as e:
            print(f"Warning: Could not connect to Neo4j: {e}")
            self.graph = None
            self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to Neo4j."""
        return self._connected

    def get_or_create_contact(
        self,
        email: str,
        name: Optional[str] = None,
        relationship: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get an existing contact or create a new one.

        Args:
            email: Contact's email address (unique identifier)
            name: Display name
            relationship: How they relate to user

        Returns:
            Contact node data or None if not connected
        """
        if not self.graph:
            return None

        # Clean email
        email = email.lower().strip()

        # Try to find existing contact
        query = """
        MATCH (c:Contact {email: $email})
        RETURN c, elementId(c) as id
        """
        result = self.graph.raw_query(query, {"email": email})

        if result:
            contact_data = dict(result[0]['c'])
            contact_data['id'] = result[0]['id']
            return contact_data

        # Create new contact
        now = datetime.utcnow().isoformat()
        contact_data = {
            "email": email,
            "name": name or email.split('@')[0],
            "relationship": relationship,
            "first_seen": now,
            "last_interaction": now,
            "interaction_count": 1,
            "needs_relationship_clarification": relationship is None,
        }

        query = """
        CREATE (c:Contact $props)
        RETURN c, elementId(c) as id
        """
        result = self.graph.raw_query(query, {"props": contact_data})

        if result:
            contact_data['id'] = result[0]['id']

            # Link to user
            self._link_contact_to_user(contact_data['id'])

            return contact_data

        return None

    def _link_contact_to_user(self, contact_id: str):
        """Create relationship between contact and user."""
        if not self.graph:
            return

        try:
            query = """
            MATCH (u:User)
            MATCH (c:Contact) WHERE elementId(c) = $contact_id
            MERGE (u)-[r:KNOWS]->(c)
            ON CREATE SET r.created_at = datetime()
            """
            self.graph.raw_query(query, {"contact_id": contact_id})
        except Exception as e:
            print(f"Error linking contact to user: {e}")

    def update_interaction(self, email: str, context: Optional[str] = None):
        """
        Record an interaction with a contact.

        Args:
            email: Contact's email
            context: Context of the interaction (e.g., "Email about project X")
        """
        if not self.graph:
            return

        email = email.lower().strip()
        now = datetime.utcnow().isoformat()

        query = """
        MATCH (c:Contact {email: $email})
        SET c.last_interaction = $now,
            c.interaction_count = COALESCE(c.interaction_count, 0) + 1
        """
        params = {"email": email, "now": now}

        if context:
            query += ", c.last_context = $context"
            params["context"] = context

        query += " RETURN c"

        self.graph.raw_query(query, params)

    def set_relationship(self, email: str, relationship: str):
        """
        Set the relationship type for a contact.

        Common relationship types:
        - colleague: Work colleague
        - friend: Personal friend
        - family: Family member
        - recruiter: Job recruiter
        - client: Client/customer
        - vendor: Vendor/service provider
        - mentor: Mentor or advisor
        - mentee: Someone you mentor
        - unknown: Not yet classified

        Args:
            email: Contact's email
            relationship: Relationship type
        """
        if not self.graph:
            return

        email = email.lower().strip()

        query = """
        MATCH (c:Contact {email: $email})
        SET c.relationship = $relationship,
            c.needs_relationship_clarification = false
        RETURN c
        """
        self.graph.raw_query(query, {"email": email, "relationship": relationship})

    def process_email_contact(
        self,
        email: str,
        name: Optional[str] = None,
        context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process a contact discovered from email.

        Creates or updates the contact and records the interaction.

        Args:
            email: Contact's email address
            name: Contact's name (if known)
            context: Context (e.g., email subject)

        Returns:
            Contact data dict
        """
        if not email or '@' not in email:
            return None

        contact = self.get_or_create_contact(email, name)

        if contact and context:
            self.update_interaction(email, context)

        return contact

    def find_contact(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for contacts by name or email.

        Args:
            query: Search string

        Returns:
            List of matching contacts
        """
        if not self.graph:
            return []

        cypher = """
        MATCH (c:Contact)
        WHERE toLower(c.name) CONTAINS toLower($query)
           OR toLower(c.email) CONTAINS toLower($query)
        RETURN c, elementId(c) as id
        ORDER BY c.interaction_count DESC
        LIMIT 20
        """
        result = self.graph.raw_query(cypher, {"query": query})

        contacts = []
        for row in result:
            contact_data = dict(row['c'])
            contact_data['id'] = row['id']
            contacts.append(contact_data)

        return contacts

    def get_contacts_needing_clarification(self) -> List[Dict[str, Any]]:
        """
        Get contacts that need relationship clarification.

        The agent can use this to ask the user about unknown contacts.

        Returns:
            List of contacts with unknown relationships
        """
        if not self.graph:
            return []

        query = """
        MATCH (c:Contact)
        WHERE c.needs_relationship_clarification = true
        RETURN c, elementId(c) as id
        ORDER BY c.interaction_count DESC
        LIMIT 10
        """
        result = self.graph.raw_query(query)

        contacts = []
        for row in result:
            contact_data = dict(row['c'])
            contact_data['id'] = row['id']
            contacts.append(contact_data)

        return contacts

    def get_frequent_contacts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most frequently interacted contacts."""
        if not self.graph:
            return []

        query = """
        MATCH (c:Contact)
        WHERE c.interaction_count > 0
        RETURN c, elementId(c) as id
        ORDER BY c.interaction_count DESC
        LIMIT $limit
        """
        result = self.graph.raw_query(query, {"limit": limit})

        contacts = []
        for row in result:
            contact_data = dict(row['c'])
            contact_data['id'] = row['id']
            contacts.append(contact_data)

        return contacts

    def get_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a contact by email address."""
        if not self.graph:
            return None

        email = email.lower().strip()

        query = """
        MATCH (c:Contact {email: $email})
        RETURN c, elementId(c) as id
        """
        result = self.graph.raw_query(query, {"email": email})

        if result:
            contact_data = dict(result[0]['c'])
            contact_data['id'] = result[0]['id']
            return contact_data

        return None


# Convenience function for email processing

def extract_contact_from_email(
    email: str,
    name: Optional[str] = None,
    context: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Extract and store a contact from an email interaction.

    This is the main function the agent should use when processing emails.

    Args:
        email: Email address
        name: Name if known
        context: Context of the email (subject, etc.)

    Returns:
        Contact data or None
    """
    manager = ContactManager()
    return manager.process_email_contact(email, name, context)
