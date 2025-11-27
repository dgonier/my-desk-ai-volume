"""
Private Services Package - Personal Data Access with OAuth

This package provides authenticated access to personal services like:
- Gmail (read emails, extract contacts)
- LinkedIn (profile data, connections)
- Calendar (Google Calendar integration)

All discovered contacts and relationships are tracked in the Neo4j cognitive graph.
"""

from .gmail import GmailService, read_recent_emails, search_emails
from .contacts import ContactManager, extract_contact_from_email
from .oauth import OAuthManager, get_oauth_status, initiate_oauth

__all__ = [
    # Gmail
    'GmailService',
    'read_recent_emails',
    'search_emails',
    # Contacts (Neo4j integration)
    'ContactManager',
    'extract_contact_from_email',
    # OAuth management
    'OAuthManager',
    'get_oauth_status',
    'initiate_oauth',
]
