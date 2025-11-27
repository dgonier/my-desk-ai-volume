"""
Job search and tracking functionality.

Uses jobspy for scraping job boards and stores results in Neo4j.
"""

import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add packages to path
sys.path.insert(0, '/packages')

from cognitive import get_graph, NodeType, RelationType
from cognitive.models import JobNode


def search_jobs(
    search_term: str,
    location: str,
    sites: Optional[List[str]] = None,
    results_wanted: int = 20,
    hours_old: int = 72,
    is_remote: bool = False,
    save_to_graph: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for jobs using jobspy and optionally save to graph.

    Args:
        search_term: Job title or keywords
        location: Location string (e.g., "Denver, CO")
        sites: Job sites to search (default: ["indeed", "linkedin"])
        results_wanted: Max results per site
        hours_old: Only jobs posted within this many hours
        is_remote: Filter for remote jobs
        save_to_graph: Whether to save results to Neo4j

    Returns:
        List of job dicts
    """
    try:
        from jobspy import scrape_jobs
    except ImportError:
        return {"error": "jobspy not installed. Add to image dependencies."}

    sites = sites or ["indeed", "linkedin"]

    try:
        jobs_df = scrape_jobs(
            site_name=sites,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            is_remote=is_remote,
            country_indeed="USA"
        )

        # Convert DataFrame to list of dicts
        jobs = jobs_df.to_dict('records') if len(jobs_df) > 0 else []

        # Normalize field names
        normalized_jobs = []
        for job in jobs:
            normalized = {
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "salary": _format_salary(job),
                "url": job.get("job_url", ""),
                "description": job.get("description", ""),
                "job_type": _infer_job_type(job),
                "level": _infer_level(job.get("title", "")),
                "source": job.get("site", ""),
                "posted_date": job.get("date_posted"),
            }
            normalized_jobs.append(normalized)

        # Save to graph if requested
        if save_to_graph and normalized_jobs:
            _save_jobs_to_graph(normalized_jobs, search_term)

        return normalized_jobs

    except Exception as e:
        return {"error": str(e)}


def _format_salary(job: Dict) -> Optional[str]:
    """Format salary from job data."""
    min_sal = job.get("min_amount")
    max_sal = job.get("max_amount")
    interval = job.get("interval", "yearly")

    if min_sal and max_sal:
        return f"${min_sal:,.0f} - ${max_sal:,.0f} {interval}"
    elif min_sal:
        return f"${min_sal:,.0f}+ {interval}"
    elif max_sal:
        return f"Up to ${max_sal:,.0f} {interval}"
    return None


def _infer_job_type(job: Dict) -> str:
    """Infer job type (remote/hybrid/onsite) from job data."""
    is_remote = job.get("is_remote", False)
    location = str(job.get("location", "")).lower()

    if is_remote or "remote" in location:
        return "remote"
    elif "hybrid" in location:
        return "hybrid"
    return "onsite"


def _infer_level(title: str) -> str:
    """Infer job level from title."""
    title_lower = title.lower()
    if any(x in title_lower for x in ["senior", "sr.", "lead", "principal", "staff"]):
        return "senior"
    elif any(x in title_lower for x in ["junior", "jr.", "entry", "associate", "i ", " i"]):
        return "entry"
    return "mid"


def _save_jobs_to_graph(jobs: List[Dict], search_term: str) -> int:
    """Save jobs to the cognitive graph."""
    graph = get_graph()
    user = graph.get_user()
    count = 0

    # Create or get topic for this search
    topic = graph.get_or_create_topic(
        f"Job Search: {search_term}",
        category="job_search"
    )

    for job in jobs:
        try:
            # Create job node
            job_node = JobNode.create(
                title=job["title"],
                company=job["company"],
                location=job.get("location"),
                salary=job.get("salary"),
                url=job.get("url"),
                description=job.get("description"),
                job_type=job.get("job_type"),
                level=job.get("level"),
            )

            job_id = graph.create_node(job_node)

            # Link to topic
            graph.create_relationship(
                job_id,
                topic["id"],
                RelationType.ABOUT_TOPIC
            )

            # Link user to job (INTERESTED_IN relationship)
            if user:
                graph.create_relationship(
                    user["id"],
                    job_id,
                    RelationType.INTERESTED_IN,
                    {"search_term": search_term}
                )

            count += 1

        except Exception as e:
            print(f"Error saving job: {e}")

    return count


def save_job(
    title: str,
    company: str,
    location: Optional[str] = None,
    salary: Optional[str] = None,
    url: Optional[str] = None,
    description: Optional[str] = None,
    job_type: Optional[str] = None,
    level: Optional[str] = None,
    **extra_props
) -> str:
    """
    Save a single job to the cognitive graph.

    Returns:
        Neo4j element ID of the created job node
    """
    graph = get_graph()

    job_node = JobNode.create(
        title=title,
        company=company,
        location=location,
        salary=salary,
        url=url,
        description=description,
        job_type=job_type,
        level=level,
        **extra_props
    )

    return graph.create_node(job_node)


def get_jobs(
    company: Optional[str] = None,
    job_type: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get jobs from the cognitive graph.

    Args:
        company: Filter by company name
        job_type: Filter by type (remote, hybrid, onsite)
        level: Filter by level (entry, mid, senior)
        limit: Maximum jobs to return

    Returns:
        List of job dicts
    """
    graph = get_graph()

    filters = {}
    if company:
        filters["company"] = company
    if job_type:
        filters["job_type"] = job_type
    if level:
        filters["level"] = level

    return graph.find_nodes(NodeType.JOB, filters if filters else None, limit)


def get_applied_jobs() -> List[Dict[str, Any]]:
    """Get all jobs the user has applied to."""
    graph = get_graph()
    user = graph.get_user()

    if not user:
        return []

    return graph.get_related_nodes(
        user["id"],
        rel_type=RelationType.APPLIED_TO,
        target_type=NodeType.JOB
    )


def mark_job_applied(
    job_id: str,
    applied_date: Optional[datetime] = None,
    notes: Optional[str] = None
) -> bool:
    """
    Mark a job as applied.

    Args:
        job_id: Neo4j element ID of the job
        applied_date: Date applied (default: now)
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
    }
    if notes:
        props["notes"] = notes

    return graph.create_relationship(
        user["id"],
        job_id,
        RelationType.APPLIED_TO,
        props
    )


def search_jobs_for_user() -> Dict[str, Any]:
    """
    Search jobs using the user's profile preferences.

    This is the convenience function for "find jobs for me" requests.
    """
    graph = get_graph()
    user = graph.get_user()

    if not user:
        return {"error": "No user profile found. Please set up your profile first."}

    # Get user preferences
    first_name = user.get("first_name", "User")
    city = user.get("city", "")
    state = user.get("state", "")
    job_titles = user.get("job_titles", ["Software Engineer"])
    remote_pref = user.get("remote_preference", "flexible")

    location = f"{city}, {state}" if city and state else "United States"
    is_remote = remote_pref in ["remote", "flexible"]

    all_jobs = []

    # Search for each job title
    for title in job_titles[:2]:  # Limit to first 2 titles
        jobs = search_jobs(
            search_term=title,
            location=location,
            results_wanted=15,
            hours_old=72,
            is_remote=is_remote,
            save_to_graph=True
        )
        if isinstance(jobs, list):
            all_jobs.extend(jobs)

    return {
        "user": first_name,
        "location": location,
        "job_titles": job_titles[:2],
        "jobs_found": len(all_jobs),
        "message": f"Found {len(all_jobs)} jobs for {first_name} in {location}. View at /app/jobs-feed"
    }
