"""
Gmail Service - Read and Search Emails

Uses Google Gmail API to access emails.
Automatically extracts contacts and stores them in Neo4j.
"""

import os
import base64
import email
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class EmailMessage:
    """Represents an email message."""
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    recipients: List[str]
    date: datetime
    snippet: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    labels: List[str] = None
    attachments: List[Dict[str, str]] = None


class GmailService:
    """
    Gmail API service for reading emails.

    Requires OAuth token with gmail.readonly scope.
    """

    BASE_URL = "https://gmail.googleapis.com/gmail/v1"

    def __init__(self):
        from .oauth import get_oauth_manager
        self.oauth = get_oauth_manager()
        self._user_email = None

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        token = self.oauth.get_token('gmail')
        if not token:
            raise ValueError("Not authenticated with Gmail. Run OAuth flow first.")
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    def is_authenticated(self) -> bool:
        """Check if Gmail is authenticated."""
        return self.oauth.is_authenticated('gmail')

    def get_profile(self) -> Dict[str, Any]:
        """Get the authenticated user's Gmail profile."""
        import httpx

        response = httpx.get(
            f"{self.BASE_URL}/users/me/profile",
            headers=self._get_headers()
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get profile: {response.text}")

    def list_messages(
        self,
        query: str = None,
        max_results: int = 20,
        label_ids: List[str] = None,
        include_spam_trash: bool = False
    ) -> List[Dict[str, str]]:
        """
        List messages matching criteria.

        Args:
            query: Gmail search query (e.g., "from:john@example.com")
            max_results: Maximum number of messages to return
            label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])
            include_spam_trash: Include spam and trash

        Returns:
            List of {id, threadId} dicts
        """
        import httpx

        params = {
            'maxResults': max_results,
            'includeSpamTrash': include_spam_trash,
        }

        if query:
            params['q'] = query
        if label_ids:
            params['labelIds'] = label_ids

        response = httpx.get(
            f"{self.BASE_URL}/users/me/messages",
            headers=self._get_headers(),
            params=params
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('messages', [])
        else:
            raise Exception(f"Failed to list messages: {response.text}")

    def get_message(self, message_id: str, format: str = 'full') -> EmailMessage:
        """
        Get a single email message.

        Args:
            message_id: The ID of the message
            format: 'full', 'metadata', 'minimal', or 'raw'

        Returns:
            EmailMessage object
        """
        import httpx

        response = httpx.get(
            f"{self.BASE_URL}/users/me/messages/{message_id}",
            headers=self._get_headers(),
            params={'format': format}
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get message: {response.text}")

        data = response.json()
        return self._parse_message(data)

    def _parse_message(self, data: Dict[str, Any]) -> EmailMessage:
        """Parse Gmail API message response into EmailMessage."""
        headers = {
            h['name'].lower(): h['value']
            for h in data.get('payload', {}).get('headers', [])
        }

        # Extract sender info
        sender_raw = headers.get('from', '')
        sender_email = ''
        sender_name = sender_raw

        if '<' in sender_raw and '>' in sender_raw:
            parts = sender_raw.split('<')
            sender_name = parts[0].strip().strip('"')
            sender_email = parts[1].rstrip('>')
        elif '@' in sender_raw:
            sender_email = sender_raw
            sender_name = sender_raw.split('@')[0]

        # Extract recipients
        recipients = []
        for field in ['to', 'cc', 'bcc']:
            if field in headers:
                recipients.extend([r.strip() for r in headers[field].split(',')])

        # Parse date
        date_str = headers.get('date', '')
        try:
            # Gmail dates can be complex, try multiple formats
            from email.utils import parsedate_to_datetime
            date = parsedate_to_datetime(date_str)
        except Exception:
            date = datetime.utcnow()

        # Extract body
        body_text = None
        body_html = None
        payload = data.get('payload', {})

        if 'body' in payload and payload['body'].get('data'):
            body_text = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain' and part.get('body', {}).get('data'):
                    body_text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif mime_type == 'text/html' and part.get('body', {}).get('data'):
                    body_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')

        return EmailMessage(
            id=data['id'],
            thread_id=data['threadId'],
            subject=headers.get('subject', '(no subject)'),
            sender=sender_name,
            sender_email=sender_email,
            recipients=recipients,
            date=date,
            snippet=data.get('snippet', ''),
            body_text=body_text,
            body_html=body_html,
            labels=data.get('labelIds', []),
        )

    def search(self, query: str, max_results: int = 20) -> List[EmailMessage]:
        """
        Search emails and return full messages.

        Args:
            query: Gmail search query (same syntax as Gmail web)
            max_results: Max messages to return

        Returns:
            List of EmailMessage objects
        """
        message_ids = self.list_messages(query=query, max_results=max_results)
        messages = []

        for msg_info in message_ids:
            try:
                msg = self.get_message(msg_info['id'])
                messages.append(msg)
            except Exception as e:
                print(f"Error fetching message {msg_info['id']}: {e}")

        return messages

    def get_recent_unread(self, max_results: int = 10) -> List[EmailMessage]:
        """Get recent unread messages."""
        return self.search("is:unread", max_results=max_results)

    def get_from_sender(self, email_address: str, max_results: int = 20) -> List[EmailMessage]:
        """Get messages from a specific sender."""
        return self.search(f"from:{email_address}", max_results=max_results)


# Convenience functions

def read_recent_emails(max_results: int = 10, unread_only: bool = False) -> List[Dict[str, Any]]:
    """
    Read recent emails and return as dictionaries.

    This function also extracts contacts and stores them in Neo4j.

    Args:
        max_results: Number of emails to fetch
        unread_only: Only get unread emails

    Returns:
        List of email data dicts
    """
    gmail = GmailService()

    if not gmail.is_authenticated():
        return [{"error": "Not authenticated with Gmail. Please complete OAuth flow."}]

    try:
        if unread_only:
            messages = gmail.get_recent_unread(max_results)
        else:
            messages = gmail.search("", max_results)

        # Process contacts from emails
        from .contacts import ContactManager
        contacts = ContactManager()

        results = []
        for msg in messages:
            # Store sender as contact in Neo4j
            contacts.process_email_contact(
                email=msg.sender_email,
                name=msg.sender,
                context=f"Email: {msg.subject}"
            )

            results.append({
                "id": msg.id,
                "subject": msg.subject,
                "from": msg.sender,
                "from_email": msg.sender_email,
                "date": msg.date.isoformat(),
                "snippet": msg.snippet,
                "labels": msg.labels,
            })

        return results

    except Exception as e:
        return [{"error": str(e)}]


def search_emails(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Search emails with Gmail query syntax.

    Args:
        query: Gmail search query (e.g., "from:john subject:meeting")
        max_results: Max number of results

    Returns:
        List of email data dicts
    """
    gmail = GmailService()

    if not gmail.is_authenticated():
        return [{"error": "Not authenticated with Gmail. Please complete OAuth flow."}]

    try:
        messages = gmail.search(query, max_results)

        # Process contacts
        from .contacts import ContactManager
        contacts = ContactManager()

        results = []
        for msg in messages:
            contacts.process_email_contact(
                email=msg.sender_email,
                name=msg.sender,
                context=f"Email: {msg.subject}"
            )

            results.append({
                "id": msg.id,
                "subject": msg.subject,
                "from": msg.sender,
                "from_email": msg.sender_email,
                "date": msg.date.isoformat(),
                "snippet": msg.snippet,
                "body_preview": msg.body_text[:500] if msg.body_text else None,
                "labels": msg.labels,
            })

        return results

    except Exception as e:
        return [{"error": str(e)}]
