"""
Scholarship search and tracking functionality.

Searches for scholarships and stores them in the cognitive graph.
"""

import sys
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx
from bs4 import BeautifulSoup

# Add packages to path
sys.path.insert(0, '/packages')

from cognitive import get_graph, NodeType, RelationType


def search_scholarships(
    field_of_study: Optional[str] = None,
    degree_level: Optional[str] = None,
    amount_min: Optional[int] = None,
    keywords: Optional[List[str]] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search for scholarships.

    This is a placeholder that can be extended with actual scholarship APIs
    or web scraping from sites like:
    - Scholarships.com
    - Fastweb
    - College Board
    - Chegg

    Args:
        field_of_study: Field (e.g., "Computer Science", "Engineering")
        degree_level: Level (e.g., "undergraduate", "graduate", "phd")
        amount_min: Minimum award amount
        keywords: Additional search keywords
        limit: Maximum results

    Returns:
        List of scholarship dicts
    """
    # Placeholder - in production, implement actual scraping/API calls
    scholarships = []

    # Example structure for scholarships
    example_scholarship = {
        "name": "Example Tech Scholarship",
        "provider": "Tech Foundation",
        "amount": "$5,000",
        "deadline": "2025-03-15",
        "url": "https://example.com/scholarship",
        "description": "For students pursuing degrees in technology fields",
        "eligibility": ["US citizen", "3.0 GPA minimum", "STEM major"],
        "field_of_study": field_of_study or "Technology",
        "degree_level": degree_level or "undergraduate",
    }

    # For now, return empty - user can implement actual scraping
    return scholarships


def save_scholarship(
    name: str,
    provider: str,
    amount: Optional[str] = None,
    deadline: Optional[str] = None,
    url: Optional[str] = None,
    description: Optional[str] = None,
    eligibility: Optional[List[str]] = None,
    field_of_study: Optional[str] = None,
    degree_level: Optional[str] = None,
    **extra_props
) -> str:
    """
    Save a scholarship to the cognitive graph.

    Returns:
        Neo4j element ID of the created scholarship node
    """
    graph = get_graph()

    props = {
        "name": name,
        "provider": provider,
        "amount": amount,
        "deadline": deadline,
        "url": url,
        "description": description,
        "eligibility": eligibility or [],
        "field_of_study": field_of_study,
        "degree_level": degree_level,
        "created_at": datetime.utcnow().isoformat(),
        **extra_props
    }

    query = """
    CREATE (s:Scholarship $props)
    RETURN elementId(s) as id
    """

    with graph.session() as session:
        result = session.run(query, props=props)
        scholarship_id = result.single()["id"]

    # Link user to scholarship
    user = graph.get_user()
    if user:
        graph.create_relationship(
            user["id"],
            scholarship_id,
            RelationType.INTERESTED_IN
        )

    return scholarship_id


def get_scholarships(
    field_of_study: Optional[str] = None,
    degree_level: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get scholarships from the cognitive graph.

    Args:
        field_of_study: Filter by field
        degree_level: Filter by degree level
        limit: Maximum scholarships to return

    Returns:
        List of scholarship dicts
    """
    graph = get_graph()

    where_clauses = ["true"]
    params = {"limit": limit}

    if field_of_study:
        where_clauses.append("s.field_of_study = $field")
        params["field"] = field_of_study

    if degree_level:
        where_clauses.append("s.degree_level = $level")
        params["level"] = degree_level

    where_str = " AND ".join(where_clauses)

    query = f"""
    MATCH (s:Scholarship)
    WHERE {where_str}
    RETURN s, elementId(s) as id
    ORDER BY s.deadline ASC
    LIMIT $limit
    """

    scholarships = []
    with graph.session() as session:
        result = session.run(query, **params)
        for record in result:
            data = dict(record["s"])
            data["id"] = record["id"]
            scholarships.append(data)

    return scholarships


def mark_scholarship_applied(
    scholarship_id: str,
    applied_date: Optional[datetime] = None,
    status: str = "applied",
    notes: Optional[str] = None
) -> bool:
    """
    Mark a scholarship as applied.

    Args:
        scholarship_id: Neo4j element ID
        applied_date: Date applied
        status: Application status (applied, submitted, awarded, rejected)
        notes: Application notes

    Returns:
        True if successful
    """
    graph = get_graph()
    user = graph.get_user()

    if not user:
        return False

    props = {
        "applied_date": (applied_date or datetime.utcnow()).isoformat(),
        "status": status,
    }
    if notes:
        props["notes"] = notes

    return graph.create_relationship(
        user["id"],
        scholarship_id,
        RelationType.APPLIED_TO,
        props
    )
