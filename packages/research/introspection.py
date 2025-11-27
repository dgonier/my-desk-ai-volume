"""
Introspection Module - Build cognitive graph from Google services.

This module provides functions to:
1. Run introspection cycles that analyze user's Google data
2. Extract entities (people, organizations, events) from emails/calendar
3. Generate insights about communication patterns, priorities, relationships
4. Store all findings in the Neo4j cognitive graph

Usage:
    from research.introspection import (
        run_introspection_cycle,
        analyze_recent_communications,
        extract_contacts_network,
        analyze_schedule_patterns,
    )

    # Run a full introspection cycle
    result = run_introspection_cycle("user@gmail.com")

    # Just analyze recent emails
    insights = analyze_recent_communications("user@gmail.com", days=7)
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# Add packages to path
sys.path.insert(0, '/packages')

from research.google_services import (
    get_todays_schedule,
    get_upcoming_events,
    get_recent_emails,
    get_important_emails,
    get_contacts,
    search_contacts,
    extract_contacts_from_emails,
    extract_meeting_attendees,
    CalendarEvent,
    Email,
    Contact,
)


@dataclass
class IntrospectionResult:
    """Result of an introspection cycle."""
    cycle_id: str
    started_at: str
    completed_at: str
    status: str
    events_processed: int
    emails_processed: int
    contacts_found: int
    insights_generated: int
    entities_created: int
    errors: List[str]


@dataclass
class CommunicationInsight:
    """An insight about communication patterns."""
    insight: str
    category: str  # frequency, priority, relationship, pattern
    confidence: float
    related_entities: List[str]
    source: str  # email, calendar, combined


@dataclass
class PersonEntity:
    """A person entity extracted from communications."""
    email: str
    name: str
    relationship: str  # colleague, external, recurring, unknown
    interaction_count: int
    last_interaction: str
    context: List[str]  # meeting titles, email subjects


def _get_graph():
    """Get the cognitive graph instance."""
    from cognitive import get_graph
    return get_graph()


def _create_introspection_cycle(graph, objective: str) -> str:
    """Create a new introspection cycle in the graph."""
    from cognitive import CycleNode, CycleType, CycleStatus

    cycle = CycleNode.create(
        name=f"Introspection - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        objective=objective,
        cycle_type=CycleType.INTROSPECTION,
        status=CycleStatus.IN_PROGRESS,
        priority=7,
        context="Automated introspection of connected Google services"
    )

    cycle_id = graph.create_node(cycle)
    return cycle_id


def _store_insight(graph, cycle_id: str, insight: CommunicationInsight) -> str:
    """Store an insight in the cognitive graph."""
    from cognitive import InsightNode, RelationType

    insight_node = InsightNode.create(
        insight=insight.insight,
        source_type="introspection",
        confidence=insight.confidence,
        category=insight.category,
        related_entities=insight.related_entities,
        source=insight.source,
    )

    insight_id = graph.create_node(insight_node)

    # Link insight to cycle
    graph.create_relationship(cycle_id, insight_id, RelationType.GENERATED)

    return insight_id


def _store_person_entity(graph, person: PersonEntity) -> str:
    """Store a person entity in the cognitive graph."""
    from cognitive import EntityNode, NodeType

    # Check if person already exists
    with graph.session() as session:
        result = session.run(
            """
            MATCH (e:Entity {email: $email})
            RETURN e.id as id
            """,
            email=person.email
        )
        existing = result.single()

        if existing:
            # Update existing entity
            session.run(
                """
                MATCH (e:Entity {id: $id})
                SET e.interaction_count = e.interaction_count + $count,
                    e.last_interaction = $last_interaction,
                    e.context = $context
                """,
                id=existing["id"],
                count=person.interaction_count,
                last_interaction=person.last_interaction,
                context=person.context[:10]  # Keep last 10 contexts
            )
            return existing["id"]

    # Create new entity
    entity = EntityNode.create(
        name=person.name or person.email,
        entity_type="person",
        email=person.email,
        relationship=person.relationship,
        interaction_count=person.interaction_count,
        last_interaction=person.last_interaction,
        context=person.context[:10],
    )

    entity_id = graph.create_node(entity)
    return entity_id


def analyze_recent_communications(
    user_email: str,
    days: int = 7
) -> List[CommunicationInsight]:
    """
    Analyze recent emails and calendar events for insights.

    Returns insights about:
    - Communication patterns
    - Important contacts
    - Priorities
    - Relationship dynamics
    """
    insights = []

    # Get recent emails
    try:
        emails = get_recent_emails(user_email, max_results=50)
    except Exception as e:
        print(f"Error fetching emails: {e}")
        emails = []

    # Get upcoming events
    try:
        events = get_upcoming_events(user_email, days=days)
    except Exception as e:
        print(f"Error fetching events: {e}")
        events = []

    # Analyze email frequency by sender
    sender_counts = {}
    for email in emails:
        sender = email.from_email
        if sender:
            sender_counts[sender] = sender_counts.get(sender, 0) + 1

    # Find frequent contacts
    frequent_senders = sorted(
        sender_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    if frequent_senders:
        names = [s[0] for s in frequent_senders]
        insights.append(CommunicationInsight(
            insight=f"Most frequent email contacts this week: {', '.join(names[:3])}",
            category="relationship",
            confidence=0.9,
            related_entities=[s[0] for s in frequent_senders],
            source="email"
        ))

    # Analyze meeting load
    if events:
        total_meeting_minutes = sum(e.duration_minutes for e in events)
        meeting_count = len(events)

        insights.append(CommunicationInsight(
            insight=f"Upcoming {meeting_count} meetings totaling {total_meeting_minutes // 60} hours over next {days} days",
            category="pattern",
            confidence=0.95,
            related_entities=[],
            source="calendar"
        ))

        # Find recurring meeting partners
        all_attendees = []
        for event in events:
            all_attendees.extend([a.get('email', '') for a in event.attendees])

        attendee_counts = {}
        for att in all_attendees:
            if att and att != user_email:
                attendee_counts[att] = attendee_counts.get(att, 0) + 1

        frequent_meetings = sorted(
            attendee_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        if frequent_meetings:
            insights.append(CommunicationInsight(
                insight=f"Frequent meeting partners: {', '.join([f[0] for f in frequent_meetings[:3]])}",
                category="relationship",
                confidence=0.85,
                related_entities=[f[0] for f in frequent_meetings],
                source="calendar"
            ))

    # Analyze email subjects for priorities
    priority_keywords = ['urgent', 'important', 'asap', 'deadline', 'priority']
    priority_emails = [
        e for e in emails
        if any(kw in e.subject.lower() for kw in priority_keywords)
    ]

    if priority_emails:
        insights.append(CommunicationInsight(
            insight=f"Found {len(priority_emails)} potentially urgent emails requiring attention",
            category="priority",
            confidence=0.7,
            related_entities=[e.from_email for e in priority_emails if e.from_email],
            source="email"
        ))

    return insights


def extract_contacts_network(user_email: str) -> List[PersonEntity]:
    """
    Extract person entities from recent communications.

    Builds a network of contacts with:
    - Interaction frequency
    - Relationship type estimation
    - Context (meeting/email subjects)
    """
    people = {}

    # Extract from emails
    try:
        email_contacts = extract_contacts_from_emails(user_email, max_emails=100)
        for ec in email_contacts:
            email = ec.get('email', '')
            if email and email != user_email:
                if email not in people:
                    people[email] = {
                        'email': email,
                        'name': ec.get('name', ''),
                        'interaction_count': 0,
                        'contexts': [],
                        'last_interaction': None
                    }
                people[email]['interaction_count'] += 1
                if ec.get('subject'):
                    people[email]['contexts'].append(f"Email: {ec['subject'][:50]}")
    except Exception as e:
        print(f"Error extracting email contacts: {e}")

    # Extract from calendar
    try:
        meeting_attendees = extract_meeting_attendees(user_email, days=14)
        for ma in meeting_attendees:
            email = ma.get('email', '')
            if email and email != user_email:
                if email not in people:
                    people[email] = {
                        'email': email,
                        'name': ma.get('name', ''),
                        'interaction_count': 0,
                        'contexts': [],
                        'last_interaction': None
                    }
                people[email]['interaction_count'] += 1
                if ma.get('event_title'):
                    people[email]['contexts'].append(f"Meeting: {ma['event_title'][:50]}")
                if ma.get('event_date'):
                    people[email]['last_interaction'] = ma['event_date']
    except Exception as e:
        print(f"Error extracting meeting attendees: {e}")

    # Convert to PersonEntity objects with relationship estimation
    entities = []
    for email, data in people.items():
        # Estimate relationship type
        count = data['interaction_count']
        if count >= 5:
            relationship = "recurring"
        elif count >= 2:
            relationship = "colleague"
        else:
            relationship = "external"

        entities.append(PersonEntity(
            email=email,
            name=data['name'],
            relationship=relationship,
            interaction_count=count,
            last_interaction=data['last_interaction'] or datetime.now().isoformat(),
            context=data['contexts'][:10]
        ))

    return sorted(entities, key=lambda x: x.interaction_count, reverse=True)


def analyze_schedule_patterns(user_email: str, days: int = 30) -> List[CommunicationInsight]:
    """
    Analyze calendar patterns over time.

    Identifies:
    - Busy vs available time patterns
    - Meeting-heavy days
    - Recurring meeting patterns
    """
    insights = []

    try:
        events = get_upcoming_events(user_email, days=days)
    except Exception as e:
        print(f"Error fetching calendar: {e}")
        return insights

    if not events:
        insights.append(CommunicationInsight(
            insight="Calendar appears empty for the next 30 days",
            category="pattern",
            confidence=0.9,
            related_entities=[],
            source="calendar"
        ))
        return insights

    # Group events by day of week
    day_counts = {i: 0 for i in range(7)}  # Mon=0, Sun=6
    for event in events:
        try:
            start = datetime.fromisoformat(event.start.replace('Z', '+00:00'))
            day_counts[start.weekday()] += 1
        except:
            pass

    # Find busiest day
    busiest_day = max(day_counts.items(), key=lambda x: x[1])
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    if busiest_day[1] > 0:
        insights.append(CommunicationInsight(
            insight=f"Busiest day tends to be {day_names[busiest_day[0]]} with {busiest_day[1]} meetings in the period",
            category="pattern",
            confidence=0.8,
            related_entities=[],
            source="calendar"
        ))

    # Find recurring meeting titles
    title_counts = {}
    for event in events:
        title = event.title.lower()[:30]  # Normalize
        title_counts[title] = title_counts.get(title, 0) + 1

    recurring = [(t, c) for t, c in title_counts.items() if c >= 2]
    if recurring:
        top_recurring = sorted(recurring, key=lambda x: x[1], reverse=True)[:3]
        insights.append(CommunicationInsight(
            insight=f"Recurring meetings identified: {', '.join([t[0] for t in top_recurring])}",
            category="pattern",
            confidence=0.85,
            related_entities=[],
            source="calendar"
        ))

    return insights


def run_introspection_cycle(
    user_email: str,
    store_to_graph: bool = True
) -> IntrospectionResult:
    """
    Run a full introspection cycle.

    This function:
    1. Creates an introspection cycle in the graph
    2. Analyzes recent communications
    3. Extracts contact network
    4. Analyzes schedule patterns
    5. Stores all insights and entities in the graph

    Args:
        user_email: The user's email for Google API access
        store_to_graph: Whether to persist findings to Neo4j

    Returns:
        IntrospectionResult with summary of findings
    """
    started_at = datetime.now().isoformat()
    errors = []
    cycle_id = None
    insights_generated = 0
    entities_created = 0
    events_processed = 0
    emails_processed = 0
    contacts_found = 0

    # Initialize graph
    if store_to_graph:
        try:
            graph = _get_graph()
            cycle_id = _create_introspection_cycle(
                graph,
                f"Analyze communications for {user_email}"
            )
        except Exception as e:
            errors.append(f"Graph initialization failed: {e}")
            store_to_graph = False

    # Step 1: Analyze recent communications
    print(f"[INTROSPECTION] Analyzing recent communications for {user_email}...")
    try:
        comm_insights = analyze_recent_communications(user_email, days=7)
        for insight in comm_insights:
            if store_to_graph and cycle_id:
                _store_insight(graph, cycle_id, insight)
            insights_generated += 1
            print(f"  - {insight.insight}")
    except Exception as e:
        errors.append(f"Communication analysis failed: {e}")

    # Step 2: Extract contact network
    print(f"[INTROSPECTION] Extracting contact network...")
    try:
        people = extract_contacts_network(user_email)
        contacts_found = len(people)

        if store_to_graph:
            for person in people[:20]:  # Limit to top 20
                try:
                    _store_person_entity(graph, person)
                    entities_created += 1
                except Exception as e:
                    errors.append(f"Failed to store person {person.email}: {e}")

        print(f"  - Found {contacts_found} contacts, stored {entities_created} entities")
    except Exception as e:
        errors.append(f"Contact extraction failed: {e}")

    # Step 3: Analyze schedule patterns
    print(f"[INTROSPECTION] Analyzing schedule patterns...")
    try:
        schedule_insights = analyze_schedule_patterns(user_email, days=30)
        for insight in schedule_insights:
            if store_to_graph and cycle_id:
                _store_insight(graph, cycle_id, insight)
            insights_generated += 1
            print(f"  - {insight.insight}")
    except Exception as e:
        errors.append(f"Schedule analysis failed: {e}")

    # Mark cycle complete
    if store_to_graph and cycle_id:
        try:
            from cognitive import CycleStatus
            graph.update_node(cycle_id, {
                "status": CycleStatus.COMPLETE.value,
                "completed_at": datetime.now().isoformat(),
                "insights_count": insights_generated,
                "entities_found": entities_created,
                "errors": len(errors)
            })
        except Exception as e:
            errors.append(f"Failed to complete cycle: {e}")

    completed_at = datetime.now().isoformat()

    result = IntrospectionResult(
        cycle_id=cycle_id or "not_stored",
        started_at=started_at,
        completed_at=completed_at,
        status="completed" if not errors else "completed_with_errors",
        events_processed=events_processed,
        emails_processed=emails_processed,
        contacts_found=contacts_found,
        insights_generated=insights_generated,
        entities_created=entities_created,
        errors=errors
    )

    print(f"\n[INTROSPECTION] Cycle complete:")
    print(f"  - Insights generated: {insights_generated}")
    print(f"  - Entities created: {entities_created}")
    print(f"  - Errors: {len(errors)}")

    return result


def get_recent_insights(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent insights from the cognitive graph."""
    graph = _get_graph()

    with graph.session() as session:
        result = session.run(
            """
            MATCH (i:Insight)
            RETURN i.id as id, i.name as insight,
                   i.source_type as source, i.confidence as confidence,
                   i.category as category, i.created_at as created_at
            ORDER BY i.created_at DESC
            LIMIT $limit
            """,
            limit=limit
        )

        return [dict(r) for r in result]


def get_person_network(min_interactions: int = 2) -> List[Dict[str, Any]]:
    """Get the network of people from the cognitive graph."""
    graph = _get_graph()

    with graph.session() as session:
        result = session.run(
            """
            MATCH (e:Entity {entity_type: 'person'})
            WHERE e.interaction_count >= $min_interactions
            RETURN e.name as name, e.email as email,
                   e.relationship as relationship,
                   e.interaction_count as interactions,
                   e.context as context
            ORDER BY e.interaction_count DESC
            """,
            min_interactions=min_interactions
        )

        return [dict(r) for r in result]
