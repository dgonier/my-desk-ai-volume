"""
Cognitive Cycles - Iterative graph building through focused research.

A cycle is a single unit of work that:
1. Examines current graph state (what do we know?)
2. Identifies a question to explore (from input OR finds gaps)
3. Does targeted research to answer that question
4. Adds findings to the graph
5. Completes

Cycles can be:
- Question-driven: "Who is John Hines to me?"
- Self-directed: Agent finds gaps/holes in the graph and fills them

Usage:
    from research.cycles import run_cycle, run_cycles

    # Question-driven cycle
    result = run_cycle(
        user_email="user@gmail.com",
        question="Who is John Hines to me?"
    )

    # Self-directed cycle (agent picks the question)
    result = run_cycle(user_email="user@gmail.com")

    # Run multiple self-directed cycles
    results = run_cycles(user_email="user@gmail.com", count=3)
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field

# Add packages to path
sys.path.insert(0, '/packages')


@dataclass
class CycleResult:
    """Result of a single cycle."""
    cycle_id: str
    question: str
    question_source: str  # "user" or "self_directed"
    findings: List[str]
    nodes_created: int
    relationships_created: int
    status: str  # "completed", "partial", "failed"
    duration_seconds: float
    error: Optional[str] = None


def _get_graph():
    """Get the cognitive graph instance."""
    from cognitive import get_graph
    return get_graph()


def _get_graph_state(graph) -> Dict[str, Any]:
    """
    Examine current state of the graph.

    Returns counts and samples of what we know.
    """
    state = {
        "people_count": 0,
        "people_sample": [],
        "insights_count": 0,
        "recent_insights": [],
        "organizations_count": 0,
        "has_user_profile": False,
        "user_name": None,
        "gaps": []
    }

    with graph.session() as session:
        # Count and sample people
        result = session.run("""
            MATCH (p:Person)
            RETURN count(p) as count
        """)
        record = result.single()
        state["people_count"] = record["count"] if record else 0

        # Sample people (most recent)
        result = session.run("""
            MATCH (p:Person)
            RETURN p.name as name, p.email as email, p.relationship as relationship
            ORDER BY p.created_at DESC
            LIMIT 5
        """)
        state["people_sample"] = [dict(r) for r in result]

        # Count insights
        result = session.run("""
            MATCH (i:Insight)
            RETURN count(i) as count
        """)
        record = result.single()
        state["insights_count"] = record["count"] if record else 0

        # Recent insights
        result = session.run("""
            MATCH (i:Insight)
            RETURN i.name as insight, i.source_type as source
            ORDER BY i.created_at DESC
            LIMIT 3
        """)
        state["recent_insights"] = [dict(r) for r in result]

        # Check for User node
        result = session.run("""
            MATCH (u:User)
            RETURN u.first_name as first_name, u.last_name as last_name
            LIMIT 1
        """)
        record = result.single()
        if record:
            state["has_user_profile"] = True
            state["user_name"] = f"{record['first_name']} {record.get('last_name', '')}".strip()

        # Count organizations
        result = session.run("""
            MATCH (o:Organization)
            RETURN count(o) as count
        """)
        record = result.single()
        state["organizations_count"] = record["count"] if record else 0

        # Identify gaps
        if state["people_count"] == 0:
            state["gaps"].append("No people in graph - need to discover contacts")
        if state["insights_count"] == 0:
            state["gaps"].append("No insights generated - need to analyze patterns")
        if not state["has_user_profile"]:
            state["gaps"].append("No user profile - need to establish identity")
        if state["organizations_count"] == 0:
            state["gaps"].append("No organizations tracked - need to identify workplaces")

        # Check for people without relationship context
        result = session.run("""
            MATCH (p:Person)
            WHERE p.relationship IS NULL OR p.relationship = 'unknown'
            RETURN count(p) as count
        """)
        record = result.single()
        unknown_relationships = record["count"] if record else 0
        if unknown_relationships > 0:
            state["gaps"].append(f"{unknown_relationships} people with unknown relationship type")

    return state


def _generate_question(graph_state: Dict[str, Any]) -> str:
    """
    Generate a question based on gaps in the graph.

    Prioritizes:
    1. Basic identity (if no user profile)
    2. Contact discovery (if no people)
    3. Relationship enrichment (if people exist but lack context)
    4. Pattern discovery (if contacts exist but no insights)
    """
    gaps = graph_state.get("gaps", [])

    # Priority 1: User profile
    if not graph_state.get("has_user_profile"):
        return "Who am I? Establish basic user identity from connected services."

    # Priority 2: Discover contacts
    if graph_state.get("people_count", 0) == 0:
        return "Who are the key people I interact with? Discover contacts from email and calendar."

    # Priority 3: Enrich unknown relationships
    if "unknown relationship type" in str(gaps):
        # Find a specific person to research (skip obvious non-persons)
        for person in graph_state.get("people_sample", []):
            if person.get("relationship") in [None, "unknown", "external"]:
                email = person.get("email", "")
                name = person.get("name", "")
                # Skip if not a real person
                if not _is_real_person(email, name):
                    continue
                display_name = name or email.split("@")[0]
                return f"Who is {display_name} to me? What is our relationship context?"
        return "What are the relationships with my frequent contacts?"

    # Priority 4: Organization discovery
    if graph_state.get("organizations_count", 0) == 0 and graph_state.get("people_count", 0) > 0:
        return "What organizations am I connected to through my contacts?"

    # Priority 5: Pattern discovery
    if graph_state.get("insights_count", 0) < 3:
        return "What patterns exist in my communications? Who do I interact with most?"

    # Default: Look for interesting patterns
    return "What new patterns or relationships can I discover from recent activity?"


def _is_real_person(email: str, name: str = "") -> bool:
    """
    Use common sense to determine if this is a real person vs promotional/automated.

    Real people:
    - Have personal email addresses (firstname.lastname@, first@, etc.)
    - Or work emails with human names
    - Have names that look like actual human names (first + last name pattern)

    NOT real people (filter out):
    - noreply@, newsletter@, marketing@, support@, info@, hello@, team@
    - Emails from promotional domains (feverup, eventbrite, mailchimp, etc.)
    - Emails with promotional subdomains (@email., @e., @em., @sg.)
    - Company/brand names as the sender name
    - Automated notification senders
    """
    if not email:
        return False

    email_lower = email.lower()
    name_lower = (name or "").lower()

    # Obviously not a person - automated/system prefixes
    automated_prefixes = [
        'noreply', 'no-reply', 'donotreply', 'newsletter', 'marketing',
        'notifications', 'alerts', 'updates', 'mailer', 'automated',
        'info@', 'hello@', 'support@', 'help@', 'team@', 'contact@',
        'billing@', 'orders@', 'shipping@', 'feedback@', 'survey@',
        'sales@', 'service@', 'news@', 'promo@', 'promos@', 'premium@',
        'alert@', 'digest@', 'weekly@', 'daily@',
    ]
    for prefix in automated_prefixes:
        if email_lower.startswith(prefix):
            return False

    # Promotional email subdomains (company@email.company.com pattern)
    promo_subdomains = [
        '@email.', '@e.', '@em.', '@sg.', '@mgs.', '@mail.',
        '@s.', '@m.', '@t.', '@n.',  # Short subdomain patterns
    ]
    for subdomain in promo_subdomains:
        if subdomain in email_lower:
            return False

    # Obviously promotional domains - mass email senders / bulk notification services
    promo_domains = [
        'mailchimp', 'sendgrid', 'amazonses', 'mailgun', 'postmark',
        'feverup', 'eventbrite', 'ticketmaster', 'stubhub',
        'constantcontact', 'campaignmonitor', 'klaviyo',
        # Note: NOT blocking linkedin.com, uber.com, etc. - people work there!
        # Only blocking their notification subdomains above (@email., @e., etc.)
    ]
    for domain in promo_domains:
        if domain in email_lower:
            return False

    # "via" in name means forwarded/automated (e.g., "John via LinkedIn")
    if ' via ' in name_lower:
        return False

    # Brand/company name patterns in sender name
    brand_keywords = [
        'newsletter', 'weekly', 'daily', 'digest', 'update', 'alert',
        'black friday', 'thanksgiving', 'holiday', 'promo',
        'membership', 'subscription', 'team', 'club',
        # Company suffixes/patterns
        'inc', 'llc', 'corp', 'company', 'co.', '& more', 'total',
        'coach ', 'roto-', 'mutual', 'consolidated',
        # Known company service names (not people)
        'uber eats', 'doordash', 'grubhub', 'instacart', 'postmates',
        'spotify', 'netflix', 'amazon', 'google maps', 'apple music',
        'lifetime fitness', 'equinox', 'orangetheory',
    ]
    for keyword in brand_keywords:
        if keyword in name_lower:
            return False

    # Names with special characters are usually companies (e.g., "Guitar Center" not "John Smith")
    # Real person names are typically: FirstName or FirstName LastName
    # Companies often have: multiple words, special chars, etc.
    if name:
        words = name.split()
        # If name has 3+ words, more likely a company (unless it's "John David Smith" pattern)
        if len(words) >= 3:
            # Check if it looks like a person name (all words capitalized, no special chars)
            looks_like_person = all(
                word[0].isupper() and word[1:].islower() if len(word) > 1 else True
                for word in words if word.isalpha()
            )
            if not looks_like_person:
                return False

    # If it passes all checks, probably a real person
    return True


def _research_question(
    question: str,
    user_email: str,
    graph_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Research a question using available data sources.

    Returns findings that can be added to the graph.
    """
    findings = {
        "people": [],
        "organizations": [],
        "insights": [],
        "relationships": [],
        "raw_data": {}
    }

    question_lower = question.lower()

    # Import research functions
    try:
        from research.google_services import (
            get_recent_emails,
            get_upcoming_events,
            extract_contacts_from_emails,
            extract_meeting_attendees,
            get_contacts,
        )
    except ImportError as e:
        findings["insights"].append({
            "insight": f"Google services not available: {e}",
            "source": "system",
            "confidence": 1.0
        })
        return findings

    # Research based on question type
    if "who am i" in question_lower or "identity" in question_lower:
        # Try to get user info from Google contacts (self)
        try:
            contacts = get_contacts(user_email, max_results=1)
            if contacts:
                # First contact is often self
                findings["insights"].append({
                    "insight": f"User email identified as {user_email}",
                    "source": "google_contacts",
                    "confidence": 0.9
                })
        except Exception as e:
            findings["insights"].append({
                "insight": f"Could not fetch contacts: {e}",
                "source": "system",
                "confidence": 1.0
            })

    elif "who are" in question_lower or "contacts" in question_lower or "people" in question_lower:
        # Discover people from multiple sources:
        # 1. Google Contacts (most reliable - user's saved contacts)
        # 2. Recent emails (extract senders/recipients)
        # 3. Calendar meetings (attendees)

        filtered_count = 0
        filtered_examples = []
        passed_examples = []

        # SOURCE 1: Google Contacts (primary source - user's actual contacts)
        # Uses smart filtering based on metadata (source type, phone, photo, groups, etc.)
        try:
            # Fetch contacts with real_people_only=True for smart filtering
            google_contacts = get_contacts(
                user_email,
                max_results=100,
                real_people_only=True  # Uses metadata-based confidence scoring
            )
            print(f"  [DEBUG] Found {len(google_contacts)} high-confidence Google Contacts")

            for gc in google_contacts:
                contact_emails = gc.get('emails', [])
                contact_name = gc.get('name', '')
                confidence = gc.get('confidence_score', 0.5)

                if not contact_emails:
                    continue

                primary_email = contact_emails[0] if isinstance(contact_emails[0], str) else contact_emails[0]

                # Skip if same as user
                if primary_email == user_email:
                    continue

                # Weight by confidence score
                interaction_weight = int(5 * confidence) + 1

                findings["people"].append({
                    "email": primary_email,
                    "name": contact_name,
                    "source": "google_contacts",
                    "interaction_count": interaction_weight,
                    "context": [
                        "Saved in Google Contacts",
                        f"Confidence: {confidence:.0%}",
                        f"Source: {gc.get('source_type', 'unknown')}",
                    ],
                    "confidence": confidence
                })
                if len(passed_examples) < 5:
                    passed_examples.append(f"{contact_name} ({primary_email}) [{confidence:.0%}]")

            findings["raw_data"]["google_contacts_found"] = len(google_contacts)
            print(f"  [DEBUG] Real contacts from Google: {len(findings['people'])}")
            if passed_examples:
                print(f"  [DEBUG] Top contacts: {passed_examples}")
        except Exception as e:
            print(f"  [DEBUG] Google Contacts error: {e}")
            findings["insights"].append({
                "insight": f"Google Contacts fetch failed: {e}",
                "source": "system",
                "confidence": 1.0
            })

        # SOURCE 2: Extract from recent emails
        try:
            email_contacts = extract_contacts_from_emails(user_email, max_emails=50)
            print(f"  [DEBUG] Found {len(email_contacts)} raw email contacts")
            for ec in email_contacts:
                contact_email = ec.get('email', '')
                contact_name = ec.get('name', '')

                # Skip if same as user or not a real person
                if not contact_email or contact_email == user_email:
                    continue
                if not _is_real_person(contact_email, contact_name):
                    filtered_count += 1
                    if len(filtered_examples) < 5:
                        filtered_examples.append(f"{contact_name} ({contact_email})")
                    continue

                # Check if already found via Google Contacts
                existing = next((p for p in findings["people"] if p["email"] == contact_email), None)
                if existing:
                    existing["interaction_count"] += 1
                    if ec.get('subject'):
                        existing["context"].append(f"Email: {ec['subject'][:50]}")
                else:
                    findings["people"].append({
                        "email": contact_email,
                        "name": contact_name,
                        "source": "email",
                        "interaction_count": 1,
                        "context": [f"Email: {ec.get('subject', '')[:50]}"] if ec.get('subject') else []
                    })
            findings["raw_data"]["email_contacts_found"] = len(email_contacts)
            findings["raw_data"]["promotional_filtered"] = filtered_count
            if filtered_examples:
                print(f"  [DEBUG] Filtered examples: {filtered_examples}")
        except Exception as e:
            findings["insights"].append({
                "insight": f"Email contact extraction failed: {e}",
                "source": "system",
                "confidence": 1.0
            })

        try:
            meeting_attendees = extract_meeting_attendees(user_email, days=14)
            for ma in meeting_attendees:
                contact_email = ma.get('email', '')
                contact_name = ma.get('name', '')

                # Skip if same as user or not a real person
                if not contact_email or contact_email == user_email:
                    continue
                if not _is_real_person(contact_email, contact_name):
                    continue

                # Check if already found via email
                existing = next((p for p in findings["people"] if p["email"] == contact_email), None)
                if existing:
                    existing["interaction_count"] += 1
                    if ma.get('event_title'):
                        existing["context"].append(f"Meeting: {ma['event_title'][:50]}")
                else:
                    findings["people"].append({
                        "email": contact_email,
                        "name": contact_name,
                        "source": "calendar",
                        "interaction_count": 1,
                        "context": [f"Meeting: {ma.get('event_title', '')[:50]}"] if ma.get('event_title') else []
                    })
            findings["raw_data"]["meeting_attendees_found"] = len(meeting_attendees)
        except Exception as e:
            findings["insights"].append({
                "insight": f"Calendar extraction failed: {e}",
                "source": "system",
                "confidence": 1.0
            })

    elif "who is" in question_lower:
        # Research a specific person
        # Extract name from question
        import re
        match = re.search(r'who is ([^?]+)', question_lower)
        if match:
            search_name = match.group(1).strip()

            # Search in emails
            try:
                emails = get_recent_emails(user_email, max_results=100)
                person_emails = [e for e in emails if search_name.lower() in (e.from_name or '').lower()
                                or search_name.lower() in (e.from_email or '').lower()]

                if person_emails:
                    # Analyze interaction patterns
                    subjects = [e.subject for e in person_emails[:10]]
                    findings["insights"].append({
                        "insight": f"Found {len(person_emails)} emails involving '{search_name}'. Topics: {', '.join(subjects[:3])}",
                        "source": "email_analysis",
                        "confidence": 0.8
                    })

                    # Get their email address
                    person_email = person_emails[0].from_email
                    findings["people"].append({
                        "email": person_email,
                        "name": person_emails[0].from_name or search_name,
                        "source": "email",
                        "interaction_count": len(person_emails),
                        "context": subjects[:5]
                    })
            except Exception as e:
                findings["insights"].append({
                    "insight": f"Email search for '{search_name}' failed: {e}",
                    "source": "system",
                    "confidence": 1.0
                })

            # Search in calendar
            try:
                events = get_upcoming_events(user_email, days=30)
                person_meetings = [e for e in events
                                  if any(search_name.lower() in str(a).lower() for a in e.attendees)]

                if person_meetings:
                    findings["insights"].append({
                        "insight": f"Found {len(person_meetings)} upcoming meetings with '{search_name}'",
                        "source": "calendar_analysis",
                        "confidence": 0.85
                    })
            except Exception as e:
                pass  # Calendar search is optional

    elif "pattern" in question_lower or "organization" in question_lower:
        # Look for organizational patterns in email domains
        try:
            email_contacts = extract_contacts_from_emails(user_email, max_emails=100)

            # Group by domain
            domains = {}
            for ec in email_contacts:
                email = ec.get('email', '')
                if '@' in email:
                    domain = email.split('@')[1]
                    if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                        domains[domain] = domains.get(domain, 0) + 1

            # Top domains are likely organizations
            top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]
            for domain, count in top_domains:
                org_name = domain.split('.')[0].title()
                findings["organizations"].append({
                    "name": org_name,
                    "domain": domain,
                    "contact_count": count
                })
                findings["insights"].append({
                    "insight": f"Frequent contact with {org_name} ({domain}) - {count} interactions",
                    "source": "email_domain_analysis",
                    "confidence": 0.7
                })
        except Exception as e:
            findings["insights"].append({
                "insight": f"Pattern analysis failed: {e}",
                "source": "system",
                "confidence": 1.0
            })

    return findings


def _add_findings_to_graph(
    graph,
    findings: Dict[str, Any],
    cycle_id: str,
    user_email: str = None
) -> Dict[str, int]:
    """
    Add research findings to the cognitive graph.

    Returns counts of nodes and relationships created.
    """
    from cognitive import NodeType, RelationType, InsightNode

    counts = {"nodes": 0, "relationships": 0}

    with graph.session() as session:
        # Ensure User node exists (for relationship creation)
        user_id = None
        if user_email:
            result = session.run("""
                MERGE (u:User {email: $email})
                ON CREATE SET u.name = $name, u.created_at = $now
                RETURN elementId(u) as id
            """, email=user_email, name=user_email.split("@")[0].title(), now=datetime.now().isoformat())
            record = result.single()
            if record:
                user_id = record["id"]

        # Add people
        for person in findings.get("people", []):
            email = person.get("email")
            if not email:
                continue

            # Check if person exists
            result = session.run("""
                MATCH (p:Person {email: $email})
                RETURN elementId(p) as id, p.interaction_count as count
            """, email=email)
            record = result.single()

            if record:
                # Update existing person
                new_count = (record["count"] or 0) + person.get("interaction_count", 1)
                session.run("""
                    MATCH (p:Person {email: $email})
                    SET p.interaction_count = $count,
                        p.updated_at = $now,
                        p.context = $context
                """,
                    email=email,
                    count=new_count,
                    now=datetime.now().isoformat(),
                    context=person.get("context", [])[:10]
                )
                # Also ensure KNOWS relationship exists for existing people
                if user_id:
                    # Estimate relationship type from interaction count
                    if new_count >= 5:
                        rel_type = "colleague"
                    elif new_count >= 2:
                        rel_type = "acquaintance"
                    else:
                        rel_type = "unknown"
                    session.run("""
                        MATCH (u:User {email: $user_email})
                        MATCH (p:Person {email: $person_email})
                        MERGE (u)-[r:KNOWS]->(p)
                        ON CREATE SET r.relationship_type = $rel_type,
                                      r.created_at = $now,
                                      r.source = $source
                        ON MATCH SET r.updated_at = $now,
                                     r.relationship_type = $rel_type
                    """,
                        user_email=user_email,
                        person_email=email,
                        rel_type=rel_type,
                        now=datetime.now().isoformat(),
                        source=person.get("source", "contacts")
                    )
                    counts["relationships"] += 1
            else:
                # Create new person
                # Estimate relationship type
                count = person.get("interaction_count", 1)
                if count >= 5:
                    relationship = "colleague"
                elif count >= 2:
                    relationship = "acquaintance"
                else:
                    relationship = "unknown"

                session.run("""
                    CREATE (p:Person {
                        name: $name,
                        email: $email,
                        relationship: $relationship,
                        interaction_count: $count,
                        source: $source,
                        context: $context,
                        created_at: $now
                    })
                """,
                    name=person.get("name") or email.split("@")[0],
                    email=email,
                    relationship=relationship,
                    count=person.get("interaction_count", 1),
                    source=person.get("source", "unknown"),
                    context=person.get("context", [])[:10],
                    now=datetime.now().isoformat()
                )
                counts["nodes"] += 1

                # Create KNOWS relationship from User to Person
                if user_id:
                    session.run("""
                        MATCH (u:User {email: $user_email})
                        MATCH (p:Person {email: $person_email})
                        MERGE (u)-[r:KNOWS]->(p)
                        ON CREATE SET r.relationship_type = $rel_type,
                                      r.created_at = $now,
                                      r.source = $source
                        ON MATCH SET r.updated_at = $now
                    """,
                        user_email=user_email,
                        person_email=email,
                        rel_type=relationship,
                        now=datetime.now().isoformat(),
                        source=person.get("source", "contacts")
                    )
                    counts["relationships"] += 1

        # Add organizations
        for org in findings.get("organizations", []):
            domain = org.get("domain")
            if not domain:
                continue

            # Check if org exists
            result = session.run("""
                MATCH (o:Organization {domain: $domain})
                RETURN elementId(o) as id
            """, domain=domain)

            if not result.single():
                session.run("""
                    CREATE (o:Organization {
                        name: $name,
                        domain: $domain,
                        contact_count: $count,
                        created_at: $now
                    })
                """,
                    name=org.get("name", domain),
                    domain=domain,
                    count=org.get("contact_count", 1),
                    now=datetime.now().isoformat()
                )
                counts["nodes"] += 1

        # Add insights
        for insight_data in findings.get("insights", []):
            insight_text = insight_data.get("insight", "")
            if not insight_text or insight_data.get("source") == "system":
                continue  # Skip system/error messages

            session.run("""
                CREATE (i:Insight {
                    name: $name,
                    insight: $insight,
                    source_type: $source,
                    confidence: $confidence,
                    created_at: $now
                })
            """,
                name=insight_text[:100],
                insight=insight_text,
                source=insight_data.get("source", "research"),
                confidence=insight_data.get("confidence", 0.7),
                now=datetime.now().isoformat()
            )
            counts["nodes"] += 1

            # Link insight to cycle
            if cycle_id:
                session.run("""
                    MATCH (c:Cycle) WHERE elementId(c) = $cycle_id
                    MATCH (i:Insight {insight: $insight})
                    CREATE (c)-[:GENERATED]->(i)
                """, cycle_id=cycle_id, insight=insight_text)
                counts["relationships"] += 1

    return counts


def run_cycle(
    user_email: str,
    question: Optional[str] = None
) -> CycleResult:
    """
    Run a single cognitive cycle.

    Args:
        user_email: User's email for accessing Google services
        question: Optional question to research. If None, agent picks one.

    Returns:
        CycleResult with findings and stats
    """
    from cognitive import CycleNode, CycleType, CycleStatus

    start_time = datetime.now()
    graph = _get_graph()

    # Step 1: Examine graph state
    print(f"\n[CYCLE] Examining graph state...")
    graph_state = _get_graph_state(graph)
    print(f"  - People in graph: {graph_state['people_count']}")
    print(f"  - Insights: {graph_state['insights_count']}")
    print(f"  - Gaps identified: {len(graph_state['gaps'])}")

    # Step 2: Determine question
    if question:
        question_source = "user"
        print(f"[CYCLE] User question: {question}")
    else:
        question = _generate_question(graph_state)
        question_source = "self_directed"
        print(f"[CYCLE] Self-directed question: {question}")

    # Step 3: Create cycle node
    cycle = CycleNode.create(
        name=question[:100],
        objective=question,
        cycle_type=CycleType.INTROSPECTION,
        status=CycleStatus.ACTIVE,
        priority=7,
        context=f"Source: {question_source}"
    )
    cycle_id = graph.create_node(cycle)
    print(f"[CYCLE] Created cycle: {cycle_id[:20]}...")

    # Step 4: Research
    print(f"[CYCLE] Researching...")
    try:
        findings = _research_question(question, user_email, graph_state)
        print(f"  - People found: {len(findings.get('people', []))}")
        print(f"  - Organizations found: {len(findings.get('organizations', []))}")
        print(f"  - Insights generated: {len(findings.get('insights', []))}")
    except Exception as e:
        findings = {"insights": [{"insight": f"Research failed: {e}", "source": "system", "confidence": 1.0}]}
        print(f"  - Research error: {e}")

    # Step 5: Add to graph
    print(f"[CYCLE] Adding findings to graph...")
    try:
        counts = _add_findings_to_graph(graph, findings, cycle_id, user_email)
        print(f"  - Nodes created: {counts['nodes']}")
        print(f"  - Relationships created: {counts['relationships']}")
    except Exception as e:
        counts = {"nodes": 0, "relationships": 0}
        print(f"  - Error adding to graph: {e}")

    # Step 6: Complete cycle
    duration = (datetime.now() - start_time).total_seconds()

    try:
        graph.update_node(cycle_id, {
            "status": CycleStatus.COMPLETED.value,
            "completed_at": datetime.now().isoformat(),
            "nodes_created": counts["nodes"],
            "relationships_created": counts["relationships"],
            "duration_seconds": duration
        })
    except Exception as e:
        print(f"  - Error completing cycle: {e}")

    # Compile findings list for result
    finding_texts = []
    for insight in findings.get("insights", []):
        if insight.get("source") != "system":
            finding_texts.append(insight.get("insight", ""))
    for person in findings.get("people", [])[:5]:
        finding_texts.append(f"Found contact: {person.get('name', person.get('email'))}")
    for org in findings.get("organizations", []):
        finding_texts.append(f"Identified org: {org.get('name')}")

    print(f"[CYCLE] Complete in {duration:.1f}s")

    return CycleResult(
        cycle_id=cycle_id,
        question=question,
        question_source=question_source,
        findings=finding_texts,
        nodes_created=counts["nodes"],
        relationships_created=counts["relationships"],
        status="completed",
        duration_seconds=duration
    )


def run_cycles(
    user_email: str,
    count: int = 3,
    questions: Optional[List[str]] = None
) -> List[CycleResult]:
    """
    Run multiple cognitive cycles.

    Args:
        user_email: User's email for accessing Google services
        count: Number of cycles to run
        questions: Optional list of questions. If shorter than count,
                  remaining cycles are self-directed.

    Returns:
        List of CycleResults
    """
    results = []
    questions = questions or []

    print(f"\n{'='*50}")
    print(f"Running {count} cognitive cycles")
    print(f"{'='*50}")

    for i in range(count):
        print(f"\n--- Cycle {i+1}/{count} ---")

        question = questions[i] if i < len(questions) else None
        result = run_cycle(user_email, question)
        results.append(result)

        print(f"Result: {result.status}")
        print(f"Findings: {len(result.findings)}")

    print(f"\n{'='*50}")
    print(f"Completed {count} cycles")
    total_nodes = sum(r.nodes_created for r in results)
    total_rels = sum(r.relationships_created for r in results)
    print(f"Total nodes created: {total_nodes}")
    print(f"Total relationships: {total_rels}")
    print(f"{'='*50}\n")

    return results


def get_graph_summary() -> Dict[str, Any]:
    """Get a summary of the current graph state."""
    graph = _get_graph()
    return _get_graph_state(graph)


async def run_query_cycle(
    query: str,
    user_email: str
) -> Dict[str, Any]:
    """
    Run a query-based research cycle (async wrapper).

    This is the async version for API endpoints.

    Args:
        query: The question to research
        user_email: User's email for accessing Google services

    Returns:
        Dict with status, answer, findings, etc.
    """
    import asyncio
    from dataclasses import asdict

    # Run the synchronous cycle in a thread pool to not block
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: run_cycle(user_email=user_email, question=query)
    )

    # Convert CycleResult to dict and add answer summary
    result_dict = asdict(result)

    # Generate a summary answer from findings
    if result.findings:
        answer = "\n".join(f"• {f}" for f in result.findings[:10])
    else:
        answer = "No findings from this research cycle."

    result_dict["answer"] = answer

    return result_dict
