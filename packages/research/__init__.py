"""
Research Package - Jobs, Articles, News, Scholarships, and Connected Services

This package provides functions for:
- Scraping and storing tech articles (LLM news, AI research, etc.)
- Job search and tracking (Indeed, LinkedIn, etc.)
- Scholarship finding
- News aggregation
- Google Services (Calendar, Gmail, Contacts, Drive)
- LinkedIn profile and career analysis
- Introspection cycles that build cognitive graph
- GitHub activity and repos (coming soon)

All data is stored in the Neo4j cognitive graph.

Usage:
    from research import (
        # Google Services
        get_daily_briefing,
        get_important_emails,
        get_todays_schedule,

        # Introspection
        run_introspection_cycle,
        analyze_recent_communications,

        # LinkedIn
        get_linkedin_profile,
        get_career_summary,
        get_job_recommendations_context,

        # Jobs
        search_jobs,
    )

    # Run full introspection to build cognitive graph
    result = run_introspection_cycle("user@gmail.com")

    # Get LinkedIn career context for job search
    context = get_job_recommendations_context("user@gmail.com")
    jobs = search_jobs(keywords=context["job_search_keywords"])
"""

from .articles import (
    scrape_articles,
    save_article,
    get_articles,
    search_articles,
)
from .jobs import (
    search_jobs,
    save_job,
    get_jobs,
    get_applied_jobs,
    mark_job_applied,
)
from .scholarships import (
    search_scholarships,
    save_scholarship,
    get_scholarships,
)
from .google_services import (
    # Calendar
    get_todays_schedule,
    get_upcoming_events,
    # Gmail
    get_recent_emails,
    get_important_emails,
    get_email_summary,
    # Contacts
    get_contacts,
    search_contacts,
    # Combined
    get_daily_briefing,
    # Relationship extraction
    extract_contacts_from_emails,
    extract_meeting_attendees,
)
from .introspection import (
    # Introspection cycles
    run_introspection_cycle,
    analyze_recent_communications,
    extract_contacts_network,
    analyze_schedule_patterns,
    # Query stored data
    get_recent_insights,
    get_person_network,
    # Data classes
    IntrospectionResult,
    CommunicationInsight,
    PersonEntity,
)
from .linkedin_services import (
    # LinkedIn profile
    get_linkedin_profile,
    get_profile_me,
    get_career_summary,
    analyze_career_trajectory,
    # Job recommendations
    get_job_recommendations_context,
    # Graph integration
    store_linkedin_profile_to_graph,
    get_linkedin_status,
    # Data classes
    LinkedInProfile,
    WorkExperience,
    CareerSummary,
)
from .cycles import (
    # Core cycle functions
    run_cycle,
    run_cycles,
    get_graph_summary,
    # Data classes
    CycleResult,
)

__all__ = [
    # Articles
    "scrape_articles",
    "save_article",
    "get_articles",
    "search_articles",
    # Jobs
    "search_jobs",
    "save_job",
    "get_jobs",
    "get_applied_jobs",
    "mark_job_applied",
    # Scholarships
    "search_scholarships",
    "save_scholarship",
    "get_scholarships",
    # Google Calendar
    "get_todays_schedule",
    "get_upcoming_events",
    # Google Gmail
    "get_recent_emails",
    "get_important_emails",
    "get_email_summary",
    # Google Contacts
    "get_contacts",
    "search_contacts",
    # Combined briefings
    "get_daily_briefing",
    # Relationship extraction
    "extract_contacts_from_emails",
    "extract_meeting_attendees",
    # Introspection cycles
    "run_introspection_cycle",
    "analyze_recent_communications",
    "extract_contacts_network",
    "analyze_schedule_patterns",
    "get_recent_insights",
    "get_person_network",
    "IntrospectionResult",
    "CommunicationInsight",
    "PersonEntity",
    # LinkedIn
    "get_linkedin_profile",
    "get_profile_me",
    "get_career_summary",
    "analyze_career_trajectory",
    "get_job_recommendations_context",
    "store_linkedin_profile_to_graph",
    "get_linkedin_status",
    "LinkedInProfile",
    "WorkExperience",
    "CareerSummary",
    # Cycles
    "run_cycle",
    "run_cycles",
    "get_graph_summary",
    "CycleResult",
]
