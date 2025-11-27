"""
Google Services Research Module

Provides functions to fetch and analyze data from Google APIs:
- Calendar: Events, meetings, schedule patterns
- Gmail: Emails, communication patterns, important contacts
- Contacts: People network, relationships
- Drive: Documents, projects (future)

These functions return data that can be used by:
- The relationships package to build entity graphs
- The cognitive package to store insights
- The agent to answer questions about schedule, emails, etc.

Requirements:
    pip install google-api-python-client google-auth google-auth-oauthlib

Usage:
    from research.google_services import (
        get_todays_schedule,
        get_upcoming_events,
        get_important_emails,
        get_contacts,
        get_daily_briefing,
    )

    # Get today's meetings
    schedule = get_todays_schedule("user@gmail.com")

    # Get important unread emails
    emails = get_important_emails("user@gmail.com")
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


# ============== Data Classes ==============

@dataclass
class CalendarEvent:
    """A calendar event."""
    id: str
    title: str
    start: str
    end: str
    description: str = ""
    location: str = ""
    attendees: List[Dict[str, Any]] = None
    meeting_link: str = ""
    status: str = ""
    duration_minutes: int = 0

    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Email:
    """An email message."""
    id: str
    thread_id: str
    subject: str
    sender: str
    to: str
    date: str
    snippet: str
    labels: List[str]
    is_unread: bool = False
    is_important: bool = False
    is_starred: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Contact:
    """A contact/person with rich metadata for filtering."""
    name: str
    emails: List[str]
    phones: List[str]
    organization: str = ""
    title: str = ""
    photo_url: str = ""
    # Rich metadata for filtering
    source_type: str = ""  # "CONTACT", "PROFILE", "DOMAIN_CONTACT"
    contact_groups: List[str] = None  # Group memberships
    is_starred: bool = False
    has_photo: bool = False
    confidence_score: float = 0.0  # How confident we are this is a real person

    def __post_init__(self):
        if self.contact_groups is None:
            self.contact_groups = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============== Token Management ==============

TOKEN_STORAGE_BASE = "/tokens"


def get_tokens_path() -> str:
    """Get the path to OAuth tokens directory."""
    # Check common locations
    if os.path.exists("/tokens"):
        return "/tokens"
    if os.path.exists("/home/claude/tokens"):
        return "/home/claude/tokens"
    # Fallback for local dev
    return os.path.expanduser("~/.mydesk/tokens")


def _load_oauth_tokens(user_email: str) -> Dict[str, Any]:
    """
    Load OAuth tokens from the OAuthManager's storage format.
    Checks both the new unified format and legacy per-service format.

    Priority order:
    1. Combined 'google' service (has all scopes)
    2. 'gmail' service
    3. 'calendar' service
    4. Legacy google.json file
    """
    tokens_path = get_tokens_path()

    # Try OAuthManager's unified tokens.json format first
    unified_path = f"{tokens_path}/{user_email}/tokens.json"
    if os.path.exists(unified_path):
        with open(unified_path, 'r') as f:
            all_tokens = json.load(f)
            # Prefer combined 'google' service (has all scopes)
            if 'google' in all_tokens:
                return all_tokens['google']
            # Fall back to individual services
            if 'gmail' in all_tokens:
                return all_tokens['gmail']
            if 'calendar' in all_tokens:
                return all_tokens['calendar']

    # Legacy format: separate google.json file
    legacy_path = f"{tokens_path}/{user_email}/google.json"
    if os.path.exists(legacy_path):
        with open(legacy_path, 'r') as f:
            token_data = json.load(f)
            return token_data.get('tokens', token_data)

    return None


def _save_oauth_tokens(user_email: str, service: str, tokens: Dict[str, Any]):
    """
    Save refreshed tokens back to the OAuthManager's storage format.
    """
    tokens_path = get_tokens_path()
    unified_path = f"{tokens_path}/{user_email}/tokens.json"

    all_tokens = {}
    if os.path.exists(unified_path):
        with open(unified_path, 'r') as f:
            all_tokens = json.load(f)

    # Update the specific service's tokens
    all_tokens[service] = tokens

    os.makedirs(os.path.dirname(unified_path), exist_ok=True)
    with open(unified_path, 'w') as f:
        json.dump(all_tokens, f, indent=2)


def get_google_credentials(user_email: str, service: str = 'gmail'):
    """
    Load and refresh Google credentials for a user.

    Args:
        user_email: User's email address
        service: Service name ('gmail' or 'calendar')

    Returns:
        google.oauth2.credentials.Credentials object
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    tokens = _load_oauth_tokens(user_email)

    if not tokens:
        raise ValueError(f"No Google tokens found for {user_email}. Please authenticate at https://my-desk.ai")

    # Handle both flat token format and nested format
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    if not access_token:
        raise ValueError(f"Invalid token format for {user_email}. Please re-authenticate at https://my-desk.ai")

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    )

    # Refresh if expired or about to expire
    should_refresh = False
    if creds.expired:
        should_refresh = True
    elif creds.expiry:
        # Refresh if expiring in next 5 minutes
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if (creds.expiry - now).total_seconds() < 300:
            should_refresh = True

    if should_refresh and creds.refresh_token:
        try:
            print(f"[Google] Refreshing expired token for {user_email}...")
            creds.refresh(Request())
            # Save refreshed tokens
            updated_tokens = {
                'access_token': creds.token,
                'refresh_token': creds.refresh_token,  # Keep the refresh token
                'expires_at': creds.expiry.isoformat() if creds.expiry else None,
                'refreshed_at': datetime.utcnow().isoformat()
            }
            _save_oauth_tokens(user_email, service, updated_tokens)
            print(f"[Google] Token refreshed successfully for {user_email}")
        except Exception as e:
            print(f"[Google] Token refresh failed for {user_email}: {e}")
            raise ValueError(f"Token refresh failed. Please re-authenticate at https://my-desk.ai")

    return creds


# ============== Calendar Functions ==============

def get_todays_schedule(user_email: str) -> Dict[str, Any]:
    """
    Get today's calendar schedule with summary.

    Args:
        user_email: User's email address

    Returns:
        Dictionary with:
        - date: Today's date
        - day_of_week: Day name
        - event_count: Number of events
        - total_meeting_hours: Hours in meetings
        - events: List of CalendarEvent dicts
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials(user_email)
    service = build('calendar', 'v3', credentials=creds)

    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_of_day.isoformat() + 'Z',
        timeMax=end_of_day.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    formatted_events = []
    total_meeting_minutes = 0

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))

        # Calculate duration
        duration_minutes = 0
        if 'T' in str(start) and 'T' in str(end):
            try:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
                total_meeting_minutes += duration_minutes
            except:
                pass

        formatted_events.append(CalendarEvent(
            id=event.get('id', ''),
            title=event.get('summary', 'No title'),
            start=start,
            end=end,
            description=event.get('description', ''),
            location=event.get('location', ''),
            meeting_link=event.get('hangoutLink', ''),
            duration_minutes=duration_minutes,
        ).to_dict())

    return {
        'date': now.strftime('%Y-%m-%d'),
        'day_of_week': now.strftime('%A'),
        'event_count': len(formatted_events),
        'total_meeting_hours': round(total_meeting_minutes / 60, 1),
        'events': formatted_events,
    }


def get_upcoming_events(
    user_email: str,
    days_ahead: int = 7,
    max_results: int = 20
) -> List[Dict[str, Any]]:
    """
    Get upcoming calendar events.

    Args:
        user_email: User's email address
        days_ahead: Number of days to look ahead (default 7)
        max_results: Maximum events to return

    Returns:
        List of CalendarEvent dicts
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials(user_email)
    service = build('calendar', 'v3', credentials=creds)

    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))

        attendees = []
        for attendee in event.get('attendees', []):
            attendees.append({
                'email': attendee.get('email'),
                'name': attendee.get('displayName'),
                'response': attendee.get('responseStatus'),
                'organizer': attendee.get('organizer', False),
            })

        formatted_events.append(CalendarEvent(
            id=event.get('id', ''),
            title=event.get('summary', 'No title'),
            start=start,
            end=end,
            description=event.get('description', ''),
            location=event.get('location', ''),
            attendees=attendees,
            meeting_link=event.get('hangoutLink') or event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', ''),
            status=event.get('status', ''),
        ).to_dict())

    return formatted_events


# ============== Gmail Functions ==============

def get_recent_emails(
    user_email: str,
    max_results: int = 20,
    unread_only: bool = False,
    important_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Get recent emails from Gmail.

    Args:
        user_email: User's email address
        max_results: Maximum emails to return
        unread_only: Only return unread emails
        important_only: Only return important emails

    Returns:
        List of Email dicts
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials(user_email)
    service = build('gmail', 'v1', credentials=creds)

    # Build label filters
    label_ids = []
    if unread_only:
        label_ids.append('UNREAD')
    if important_only:
        label_ids.append('IMPORTANT')

    # Get messages
    if label_ids:
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            labelIds=label_ids
        ).execute()
    else:
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
        ).execute()

    messages = results.get('messages', [])

    formatted_emails = []
    for msg in messages:
        message = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['Subject', 'From', 'To', 'Date']
        ).execute()

        headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
        labels = message.get('labelIds', [])

        formatted_emails.append(Email(
            id=message['id'],
            thread_id=message['threadId'],
            subject=headers.get('Subject', '(No subject)'),
            sender=headers.get('From', ''),
            to=headers.get('To', ''),
            date=headers.get('Date', ''),
            snippet=message.get('snippet', ''),
            labels=labels,
            is_unread='UNREAD' in labels,
            is_important='IMPORTANT' in labels,
            is_starred='STARRED' in labels,
        ).to_dict())

    return formatted_emails


def get_important_emails(user_email: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Get important/priority unread emails.

    Args:
        user_email: User's email address
        max_results: Maximum emails to return

    Returns:
        Dictionary with:
        - important_unread_count: Number of important unread
        - starred_unread_count: Number of starred unread
        - emails: List of Email dicts
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials(user_email)
    service = build('gmail', 'v1', credentials=creds)

    # Get important unread using labels
    results = service.users().messages().list(
        userId='me',
        maxResults=max_results,
        labelIds=['IMPORTANT', 'UNREAD']
    ).execute()
    important_unread = results.get('messages', [])

    # Get starred unread
    starred_results = service.users().messages().list(
        userId='me',
        maxResults=5,
        labelIds=['STARRED', 'UNREAD']
    ).execute()
    starred = starred_results.get('messages', [])

    # Combine and dedupe
    all_message_ids = set()
    all_messages = []

    for msg in important_unread + starred:
        if msg['id'] not in all_message_ids:
            all_message_ids.add(msg['id'])

            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
            labels = message.get('labelIds', [])

            all_messages.append(Email(
                id=message['id'],
                thread_id=message['threadId'],
                subject=headers.get('Subject', '(No subject)'),
                sender=headers.get('From', ''),
                to='',
                date=headers.get('Date', ''),
                snippet=message.get('snippet', ''),
                labels=labels,
                is_unread='UNREAD' in labels,
                is_important='IMPORTANT' in labels,
                is_starred='STARRED' in labels,
            ).to_dict())

    return {
        'important_unread_count': len(important_unread),
        'starred_unread_count': len(starred),
        'emails': all_messages,
    }


def get_email_summary(user_email: str) -> Dict[str, Any]:
    """
    Get inbox statistics summary.

    Args:
        user_email: User's email address

    Returns:
        Dictionary with inbox stats
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials(user_email)
    service = build('gmail', 'v1', credentials=creds)

    # Get profile
    profile = service.users().getProfile(userId='me').execute()

    # Count unread
    unread = service.users().messages().list(
        userId='me',
        maxResults=1,
        labelIds=['UNREAD']
    ).execute()

    # Count important unread
    important_unread = service.users().messages().list(
        userId='me',
        maxResults=1,
        labelIds=['IMPORTANT', 'UNREAD']
    ).execute()

    return {
        'email': profile.get('emailAddress'),
        'total_messages': profile.get('messagesTotal', 0),
        'total_threads': profile.get('threadsTotal', 0),
        'unread_count': unread.get('resultSizeEstimate', 0),
        'important_unread_count': important_unread.get('resultSizeEstimate', 0),
    }


# ============== Contacts Functions ==============

def get_contacts(
    user_email: str,
    max_results: int = 100,
    query: str = "",
    min_confidence: float = 0.0,
    real_people_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Get user's contacts from Google Contacts with rich metadata.

    Args:
        user_email: User's email address
        max_results: Maximum contacts to return
        query: Optional search query
        min_confidence: Minimum confidence score (0.0-1.0) to include
        real_people_only: If True, filter out likely businesses/automated contacts

    Returns:
        List of Contact dicts with confidence scores
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials(user_email)
    service = build('people', 'v1', credentials=creds)

    # Fetch contacts with rich metadata for filtering
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=max_results,
        personFields='names,emailAddresses,phoneNumbers,organizations,photos,metadata,memberships,biographies',
    ).execute()

    connections = results.get('connections', [])

    formatted_contacts = []
    for person in connections:
        names = person.get('names', [])
        emails = person.get('emailAddresses', [])
        phones = person.get('phoneNumbers', [])
        orgs = person.get('organizations', [])
        photos = person.get('photos', [])
        metadata = person.get('metadata', {})
        memberships = person.get('memberships', [])

        name = names[0].get('displayName') if names else 'Unknown'

        # Filter by query if provided
        if query:
            query_lower = query.lower()
            searchable = f"{name} {' '.join(e.get('value', '') for e in emails)}".lower()
            if query_lower not in searchable:
                continue

        # Extract source type from metadata
        sources = metadata.get('sources', [])
        source_type = sources[0].get('type', '') if sources else ''

        # Check profileMetadata for objectType (PERSON vs PAGE)
        # PAGE type indicates a business/brand page, not a real person
        is_business_page = False
        for source in sources:
            profile_metadata = source.get('profileMetadata', {})
            if profile_metadata:
                object_type = profile_metadata.get('objectType', '')
                if object_type == 'PAGE':
                    is_business_page = True
                    break

        # Skip business pages entirely
        if is_business_page:
            continue

        # Extract contact groups from memberships
        contact_groups = []
        is_starred = False
        for membership in memberships:
            group_membership = membership.get('contactGroupMembership', {})
            group_id = group_membership.get('contactGroupResourceName', '')
            if group_id:
                # Extract group name from resource name
                group_name = group_id.split('/')[-1] if '/' in group_id else group_id
                contact_groups.append(group_name)
                if 'starred' in group_name.lower():
                    is_starred = True

        # Check if has real photo (not default)
        has_photo = False
        if photos:
            photo_metadata = photos[0].get('metadata', {})
            # Default photos have 'default' set to true
            if not photo_metadata.get('default', True):
                has_photo = True

        # Calculate confidence score for being a real person
        confidence = _calculate_contact_confidence(
            name=name,
            emails=[e.get('value', '') for e in emails],
            phones=[p.get('value', '') for p in phones],
            organization=orgs[0].get('name', '') if orgs else '',
            title=orgs[0].get('title', '') if orgs else '',
            source_type=source_type,
            contact_groups=contact_groups,
            is_starred=is_starred,
            has_photo=has_photo
        )

        # Apply filters
        if confidence < min_confidence:
            continue

        # More selective threshold - 0.55 filters out borderline cases
        if real_people_only and confidence < 0.55:
            continue

        formatted_contacts.append(Contact(
            name=name,
            emails=[e.get('value') for e in emails],
            phones=[p.get('value') for p in phones],
            organization=orgs[0].get('name', '') if orgs else '',
            title=orgs[0].get('title', '') if orgs else '',
            photo_url=photos[0].get('url', '') if photos else '',
            source_type=source_type,
            contact_groups=contact_groups,
            is_starred=is_starred,
            has_photo=has_photo,
            confidence_score=confidence,
        ).to_dict())

    # Sort by confidence score (highest first)
    formatted_contacts.sort(key=lambda x: x['confidence_score'], reverse=True)

    return formatted_contacts


def _calculate_contact_confidence(
    name: str,
    emails: List[str],
    phones: List[str],
    organization: str,
    title: str,
    source_type: str,
    contact_groups: List[str],
    is_starred: bool,
    has_photo: bool
) -> float:
    """
    Calculate confidence score (0.0-1.0) that this contact is a real person.

    Higher scores = more likely a real person you know
    Lower scores = more likely automated/business/promotional

    Scoring factors:
    - Source type (manually added vs auto-imported)
    - Has phone number (real contacts often have phones)
    - Has organization + title (professionals)
    - Has custom photo
    - Is starred
    - Is in contact groups
    - Name pattern analysis
    - Email pattern analysis
    """
    score = 0.0
    max_score = 0.0

    # Source type (max 0.2)
    max_score += 0.2
    if source_type == 'CONTACT':
        score += 0.2  # Manually added - strong signal
    elif source_type == 'PROFILE':
        score += 0.15  # From Google profile
    elif source_type == 'DOMAIN_CONTACT':
        score += 0.1  # Workspace directory

    # Has phone number (max 0.15)
    max_score += 0.15
    if phones:
        score += 0.15

    # Has organization (max 0.1)
    max_score += 0.1
    if organization:
        score += 0.1

    # Has job title (max 0.1)
    max_score += 0.1
    if title:
        score += 0.1

    # Has custom photo (max 0.1)
    max_score += 0.1
    if has_photo:
        score += 0.1

    # Is starred (max 0.15)
    max_score += 0.15
    if is_starred:
        score += 0.15

    # Is in contact groups (max 0.1)
    max_score += 0.1
    if contact_groups:
        score += 0.1

    # Name pattern analysis (max 0.1)
    max_score += 0.1
    name_score = _analyze_name_pattern(name)
    score += 0.1 * name_score

    # Email pattern analysis - penalize automated patterns
    if emails:
        email = emails[0].lower()
        # Penalize noreply, newsletter, etc.
        automated_patterns = [
            'noreply', 'no-reply', 'newsletter', 'marketing', 'notifications',
            'alerts', 'updates', 'mailer', 'info@', 'hello@', 'support@',
            'team@', 'sales@', 'service@'
        ]
        for pattern in automated_patterns:
            if pattern in email:
                score -= 0.3  # Heavy penalty

        # Penalize promotional subdomains
        promo_subdomains = ['@email.', '@e.', '@em.', '@sg.', '@mail.']
        for subdomain in promo_subdomains:
            if subdomain in email:
                score -= 0.2

    # Normalize to 0-1 range
    score = max(0.0, min(1.0, score / max_score if max_score > 0 else 0))

    return round(score, 2)


def _analyze_name_pattern(name: str) -> float:
    """
    Analyze if a name looks like a real person's name.

    Returns 0.0-1.0 score.
    """
    if not name or name == 'Unknown':
        return 0.0

    name_lower = name.lower()
    name_stripped = name.strip()

    # Strong company indicators - return very low score
    # Names starting with "The" are almost always companies/brands
    if name_stripped.startswith('The ') or name_stripped.startswith('the '):
        return 0.05

    # Penalize company/brand patterns - expanded list
    brand_keywords = [
        # Email/notification patterns
        'newsletter', 'weekly', 'daily', 'digest', 'update', 'alert',
        'notification', 'noreply', 'no-reply', 'mailer',
        # Business suffixes
        'inc', 'llc', 'corp', 'company', 'team', 'support', 'ltd', 'gmbh',
        # Common service/product names
        'uber eats', 'doordash', 'grubhub', 'spotify', 'netflix',
        'amazon', 'google', 'facebook', 'linkedin', 'twitter', 'instagram',
        'disney', 'samsung', 'apple', 'microsoft', 'adobe',
        # Political/org patterns
        'democrats', 'republicans', 'party', 'abroad', 'foundation',
        'association', 'society', 'institute', 'council', 'committee',
        # Media/content
        'podcast', 'chronicle', 'gazette', 'times', 'post', 'news',
        'gradient', 'journal', 'magazine', 'media', 'press',
        # Services
        'service', 'services', 'solutions', 'consulting', 'group',
        'labs', 'studio', 'studios', 'network', 'networks',
        # Ecommerce/retail
        'store', 'shop', 'market', 'marketplace', 'mall',
        # Generic business terms
        'global', 'international', 'worldwide', 'official',
    ]
    for keyword in brand_keywords:
        if keyword in name_lower:
            return 0.05

    # Check for product/service names (single capitalized word that's not a name)
    single_word_companies = [
        'disney+', 'hulu', 'peacock', 'paramount', 'hbo', 'espn',
        'airbnb', 'uber', 'lyft', 'doordash', 'instacart',
        'chase', 'citi', 'amex', 'venmo', 'paypal', 'stripe',
        'zoom', 'slack', 'asana', 'notion', 'figma', 'canva',
        'medium', 'substack', 'patreon', 'kickstarter',
    ]
    if name_lower.strip() in single_word_companies:
        return 0.05

    # Check for typical person name pattern (First Last or First)
    words = name.split()

    if len(words) == 0:
        return 0.0
    elif len(words) == 1:
        # Single word - could be first name but also single-word company
        word = words[0]
        # If all caps, likely acronym/company
        if word.isupper() and len(word) > 2:
            return 0.1
        return 0.5 if word[0].isupper() else 0.3
    elif len(words) == 2:
        # Two words - typical "First Last" pattern
        first, last = words
        # Check if it looks like "Company Name" vs "First Last"
        # Company names often have generic second words
        company_second_words = ['team', 'group', 'labs', 'studio', 'news', 'media', 'inc', 'llc']
        if last.lower() in company_second_words:
            return 0.1
        if first[0].isupper() and last[0].isupper():
            return 1.0
        return 0.6
    elif len(words) == 3:
        # Could be "First Middle Last" or company name
        # Check for org patterns like "Democrats Abroad China"
        if any(w.lower() in brand_keywords for w in words):
            return 0.1
        if all(w[0].isupper() for w in words if w):
            return 0.7  # Reduced from 0.8 - 3 words is less certain
        return 0.3
    else:
        # 4+ words - very likely a company/org name
        return 0.15

    return 0.5


def search_contacts(user_email: str, query: str) -> List[Dict[str, Any]]:
    """Search contacts by name or email."""
    return get_contacts(user_email, max_results=50, query=query)


# ============== Combined Functions ==============

def get_daily_briefing(user_email: str) -> Dict[str, Any]:
    """
    Get a comprehensive daily briefing.

    Combines:
    - Today's schedule
    - Important emails
    - Upcoming week events
    - Inbox summary

    Args:
        user_email: User's email address

    Returns:
        Complete daily briefing data
    """
    return {
        'generated_at': datetime.utcnow().isoformat(),
        'user_email': user_email,
        'today': get_todays_schedule(user_email),
        'important_emails': get_important_emails(user_email, max_results=5),
        'week_ahead': get_upcoming_events(user_email, days_ahead=7, max_results=10),
        'inbox_summary': get_email_summary(user_email),
    }


# ============== Relationship Extraction Helpers ==============

def extract_contacts_from_emails(
    user_email: str,
    max_emails: int = 100
) -> List[Dict[str, Any]]:
    """
    Extract unique contacts from recent emails.

    Useful for building relationship graph from communication patterns.

    Args:
        user_email: User's email address
        max_emails: Maximum emails to scan

    Returns:
        List of unique contacts with interaction counts
    """
    emails = get_recent_emails(user_email, max_results=max_emails)

    contacts = {}
    for email in emails:
        sender = email['sender']
        # Parse email address from "Name <email@example.com>" format
        if '<' in sender:
            name = sender.split('<')[0].strip().strip('"')
            email_addr = sender.split('<')[1].replace('>', '').strip()
        else:
            name = sender
            email_addr = sender

        if email_addr not in contacts:
            contacts[email_addr] = {
                'email': email_addr,
                'name': name,
                'interaction_count': 0,
                'last_interaction': None,
                'is_important': False,
            }

        contacts[email_addr]['interaction_count'] += 1
        contacts[email_addr]['last_interaction'] = email['date']
        if email['is_important']:
            contacts[email_addr]['is_important'] = True

    # Sort by interaction count
    return sorted(contacts.values(), key=lambda x: x['interaction_count'], reverse=True)


def extract_meeting_attendees(
    user_email: str,
    days_back: int = 30
) -> List[Dict[str, Any]]:
    """
    Extract unique meeting attendees from calendar.

    Useful for building professional relationship graph.

    Args:
        user_email: User's email address
        days_back: Days of history to scan

    Returns:
        List of unique attendees with meeting counts
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials(user_email)
    service = build('calendar', 'v3', credentials=creds)

    now = datetime.utcnow()
    time_min = (now - timedelta(days=days_back)).isoformat() + 'Z'
    time_max = now.isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        maxResults=500,
        singleEvents=True,
    ).execute()

    events = events_result.get('items', [])

    attendees = {}
    for event in events:
        for attendee in event.get('attendees', []):
            email = attendee.get('email', '')
            if not email or email == user_email:
                continue

            if email not in attendees:
                attendees[email] = {
                    'email': email,
                    'name': attendee.get('displayName', email),
                    'meeting_count': 0,
                    'meetings': [],
                }

            attendees[email]['meeting_count'] += 1
            attendees[email]['meetings'].append({
                'title': event.get('summary', 'No title'),
                'date': event['start'].get('dateTime', event['start'].get('date')),
            })

    return sorted(attendees.values(), key=lambda x: x['meeting_count'], reverse=True)
