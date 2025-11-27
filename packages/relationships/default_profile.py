"""
Default user profile setup.

This file creates the initial user profile if one doesn't exist.
"""

from datetime import datetime
from .models import UserProfile, Location, ContactInfo, Preferences
from .store import get_store


def create_default_profile() -> UserProfile:
    """
    Create the default user profile for Devin.

    This is called on first run to initialize the agent's knowledge
    of its owner.
    """
    profile = UserProfile(
        id="primary_user",
        first_name="Devin",
        location=Location(
            city="Denver",
            state="CO",
            country="USA",
            timezone="America/Denver",
        ),
        contact=ContactInfo(
            email="devin@trainfarren.com",
        ),
        preferences=Preferences(
            preferred_name="Devin",
            communication_style="casual",
            job_titles=["Software Engineer", "ML Engineer", "AI Engineer"],
            industries=["Technology", "AI/ML", "Startups"],
            remote_preference="flexible",
            skills=[
                "Python",
                "TypeScript",
                "React",
                "Modal",
                "FastAPI",
                "Machine Learning",
                "TTS",
                "LLMs",
            ],
            interests=[
                "AI",
                "Voice Technology",
                "Fitness",
                "Building Products",
            ],
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    return profile


def ensure_profile_exists(data_dir: str = "/home/claude/data/relationships") -> UserProfile:
    """
    Ensure a user profile exists, creating the default if not.

    Returns the existing or newly created profile.
    """
    store = get_store(data_dir)
    profile = store.get_user_profile()

    if profile is None:
        profile = create_default_profile()
        store.save_user_profile(profile)
        print(f"[Relationships] Created default profile for {profile.display_name}")

    return profile
