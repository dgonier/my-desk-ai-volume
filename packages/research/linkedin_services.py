"""
LinkedIn Services Research Module

Provides functions to fetch and analyze data from LinkedIn API:
- Profile: User's professional profile, experience, skills
- Connections: Professional network
- Career insights: Job history patterns, career trajectory

These functions return data that can be used by:
- The relationships package to build professional networks
- The cognitive package to store career insights
- The agent to answer questions about career background

Requirements:
    OAuth token stored at /tokens/{user_email}/linkedin.json
    Created via auth_service.py LinkedIn OAuth flow

Usage:
    from research.linkedin_services import (
        get_linkedin_profile,
        get_career_summary,
        analyze_career_trajectory,
    )

    # Get profile
    profile = get_linkedin_profile("user@gmail.com")

    # Get career analysis
    summary = get_career_summary("user@gmail.com")
"""

import os
import sys
import json
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

# Add packages to path
sys.path.insert(0, '/packages')


# ============== Data Classes ==============

@dataclass
class LinkedInProfile:
    """A LinkedIn profile."""
    id: str
    first_name: str
    last_name: str
    email: str = ""
    headline: str = ""
    location: str = ""
    profile_picture: str = ""
    public_profile_url: str = ""


@dataclass
class WorkExperience:
    """A work experience entry."""
    company: str
    title: str
    start_date: str
    end_date: str = ""  # Empty if current
    description: str = ""
    location: str = ""
    is_current: bool = False


@dataclass
class CareerSummary:
    """Summary of career trajectory."""
    total_years_experience: float
    companies_count: int
    current_role: str
    current_company: str
    industries: List[str]
    skills: List[str]
    career_progression: str  # e.g., "IC to Leadership", "Specialist", "Career Changer"


# ============== Token Management ==============

def get_tokens_path(user_email: str) -> str:
    """Get the path to user's LinkedIn tokens."""
    return f"/tokens/{user_email}/linkedin.json"


def get_linkedin_credentials(user_email: str) -> Optional[Dict[str, Any]]:
    """
    Load LinkedIn OAuth credentials for the user.

    Returns None if not authenticated.
    """
    token_path = get_tokens_path(user_email)

    if not os.path.exists(token_path):
        print(f"LinkedIn not authenticated for {user_email}")
        return None

    try:
        with open(token_path, 'r') as f:
            tokens = json.load(f)

        # Check if token is expired
        if 'expires_at' in tokens:
            expires_at = datetime.fromisoformat(tokens['expires_at'])
            if datetime.now() > expires_at:
                print(f"LinkedIn token expired for {user_email}")
                return None

        return tokens
    except Exception as e:
        print(f"Error loading LinkedIn credentials: {e}")
        return None


# ============== Profile Functions ==============

def get_linkedin_profile(user_email: str) -> Optional[LinkedInProfile]:
    """
    Get the user's LinkedIn profile.

    Uses the LinkedIn v2 API /v2/userinfo endpoint for OpenID Connect.

    Returns:
        LinkedInProfile or None if not authenticated
    """
    tokens = get_linkedin_credentials(user_email)
    if not tokens:
        return None

    access_token = tokens.get('access_token')
    if not access_token:
        print("No access token found")
        return None

    try:
        # Use userinfo endpoint (OpenID Connect)
        response = httpx.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            timeout=30.0
        )

        if response.status_code != 200:
            print(f"LinkedIn API error: {response.status_code} - {response.text}")
            return None

        data = response.json()

        return LinkedInProfile(
            id=data.get('sub', ''),
            first_name=data.get('given_name', ''),
            last_name=data.get('family_name', ''),
            email=data.get('email', ''),
            headline="",  # Not available in userinfo
            location=data.get('locale', {}).get('country', ''),
            profile_picture=data.get('picture', ''),
            public_profile_url=""
        )

    except Exception as e:
        print(f"Error fetching LinkedIn profile: {e}")
        return None


def get_profile_me(user_email: str) -> Optional[Dict[str, Any]]:
    """
    Get basic profile via /v2/me endpoint.

    Returns raw LinkedIn API response.
    """
    tokens = get_linkedin_credentials(user_email)
    if not tokens:
        return None

    access_token = tokens.get('access_token')
    if not access_token:
        return None

    try:
        response = httpx.get(
            "https://api.linkedin.com/v2/me",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            timeout=30.0
        )

        if response.status_code != 200:
            print(f"LinkedIn API error: {response.status_code} - {response.text}")
            return None

        return response.json()

    except Exception as e:
        print(f"Error fetching LinkedIn me: {e}")
        return None


# ============== Career Analysis ==============

def get_career_summary(user_email: str) -> Optional[CareerSummary]:
    """
    Get a summary of the user's career based on LinkedIn profile.

    Note: Full experience data requires r_liteprofile and r_fullprofile scopes
    which require LinkedIn Partner Program. For basic OAuth we can only get
    name, email, and profile picture.

    For now, returns a basic summary based on available data.
    """
    profile = get_linkedin_profile(user_email)
    if not profile:
        return None

    # With basic OAuth, we have limited data
    # Return a placeholder that can be enriched with manual input
    return CareerSummary(
        total_years_experience=0,  # Not available in basic OAuth
        companies_count=0,
        current_role=profile.headline or "Unknown",
        current_company="",
        industries=[],
        skills=[],
        career_progression="Unknown - requires additional LinkedIn permissions"
    )


def analyze_career_trajectory(user_email: str) -> Dict[str, Any]:
    """
    Analyze the user's career trajectory for job recommendations.

    Returns insights about:
    - Career direction (technical, management, etc.)
    - Industry preferences
    - Experience level
    - Potential next roles

    Note: With basic OAuth, this provides limited analysis.
    Full analysis requires LinkedIn Partner Program access.
    """
    profile = get_linkedin_profile(user_email)

    analysis = {
        "profile_found": profile is not None,
        "name": f"{profile.first_name} {profile.last_name}" if profile else "Unknown",
        "email": profile.email if profile else "",
        "insights": [],
        "limitations": [
            "LinkedIn basic OAuth provides limited profile data",
            "For full career analysis, manual profile input or Partner API access needed"
        ]
    }

    if profile:
        analysis["insights"].append({
            "type": "identity",
            "content": f"Profile verified for {profile.first_name} {profile.last_name}",
            "confidence": 0.95
        })

    return analysis


# ============== Job Recommendations ==============

def get_job_recommendations_context(user_email: str) -> Dict[str, Any]:
    """
    Get context for job recommendations based on LinkedIn profile.

    This context can be used by:
    - LLM agents to personalize job search
    - Job scraping functions to filter results
    - Career advice features

    Returns a dictionary that can be passed to job search functions.
    """
    profile = get_linkedin_profile(user_email)
    career = get_career_summary(user_email)

    context = {
        "has_linkedin": profile is not None,
        "name": "",
        "location": "",
        "current_role": "",
        "skills": [],
        "industries": [],
        "experience_years": 0,
        "job_search_keywords": [],
    }

    if profile:
        context["name"] = f"{profile.first_name} {profile.last_name}"
        context["location"] = profile.location

    if career:
        context["current_role"] = career.current_role
        context["skills"] = career.skills
        context["industries"] = career.industries
        context["experience_years"] = career.total_years_experience

        # Generate search keywords from career data
        keywords = []
        if career.current_role:
            keywords.append(career.current_role)
        keywords.extend(career.skills[:5])
        context["job_search_keywords"] = keywords

    return context


# ============== Integration with Cognitive Graph ==============

def store_linkedin_profile_to_graph(user_email: str) -> Optional[str]:
    """
    Store LinkedIn profile data in the cognitive graph.

    Creates or updates nodes for:
    - User profile with LinkedIn data
    - Skills as entity nodes
    - Companies as entity nodes (if experience available)

    Returns the user node ID or None if failed.
    """
    from cognitive import get_graph, NodeType

    profile = get_linkedin_profile(user_email)
    if not profile:
        return None

    graph = get_graph()

    try:
        # Update user node with LinkedIn data
        with graph.session() as session:
            result = session.run(
                """
                MATCH (u:User)
                SET u.linkedin_id = $linkedin_id,
                    u.linkedin_name = $name,
                    u.linkedin_picture = $picture,
                    u.linkedin_headline = $headline,
                    u.linkedin_location = $location,
                    u.linkedin_updated_at = $updated_at
                RETURN u.id as id
                """,
                linkedin_id=profile.id,
                name=f"{profile.first_name} {profile.last_name}",
                picture=profile.profile_picture,
                headline=profile.headline,
                location=profile.location,
                updated_at=datetime.now().isoformat()
            )
            record = result.single()
            return record["id"] if record else None

    except Exception as e:
        print(f"Error storing LinkedIn profile: {e}")
        return None


def get_linkedin_status(user_email: str) -> Dict[str, Any]:
    """
    Check LinkedIn authentication status for the user.

    Returns:
        {
            "authenticated": bool,
            "profile_available": bool,
            "token_expires_at": str or None,
            "scopes": List[str]
        }
    """
    tokens = get_linkedin_credentials(user_email)

    status = {
        "authenticated": tokens is not None,
        "profile_available": False,
        "token_expires_at": None,
        "scopes": []
    }

    if tokens:
        status["token_expires_at"] = tokens.get('expires_at')
        status["scopes"] = tokens.get('scope', '').split(' ')

        # Try to fetch profile to verify token works
        profile = get_linkedin_profile(user_email)
        status["profile_available"] = profile is not None

    return status
