"""
OAuth Management for Private Services

Handles OAuth flows for Gmail, LinkedIn, GitHub, and other services.
Stores tokens securely per-user in Modal Volume (/tokens/{user_email}/{service}.json).
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


# Token storage base path on the oauth-tokens volume
TOKEN_STORAGE_BASE = "/tokens"


class OAuthManager:
    """
    Manages OAuth tokens for various services.

    Services supported:
    - gmail: Google Gmail API (read-only access) - typically via Google login
    - calendar: Google Calendar API - typically via Google login
    - linkedin: LinkedIn API (profile, connections)
    - github: GitHub API (repos, profile, activity)
    """

    # OAuth configuration for each service
    SERVICES = {
        # Combined Google service - requests all Google scopes at once
        # This is the recommended way to authenticate for full Google access
        'google': {
            'client_id_env': 'GOOGLE_CLIENT_ID',
            'client_secret_env': 'GOOGLE_CLIENT_SECRET',
            'scopes': [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.metadata',
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/contacts.readonly',
                'https://www.googleapis.com/auth/contacts.other.readonly',
            ],
            'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
        },
        'gmail': {
            'client_id_env': 'GOOGLE_CLIENT_ID',
            'client_secret_env': 'GOOGLE_CLIENT_SECRET',
            'scopes': [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.metadata',
            ],
            'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
        },
        'calendar': {
            'client_id_env': 'GOOGLE_CLIENT_ID',
            'client_secret_env': 'GOOGLE_CLIENT_SECRET',
            'scopes': [
                'https://www.googleapis.com/auth/calendar.readonly',
            ],
            'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
        },
        'linkedin': {
            'client_id_env': 'LINKEDIN_CLIENT_ID',
            'client_secret_env': 'LINKEDIN_CLIENT_SECRET',
            'scopes': [
                'openid',
                'profile',
                'email',
            ],
            'auth_url': 'https://www.linkedin.com/oauth/v2/authorization',
            'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
        },
        'github': {
            'client_id_env': 'GITHUB_CLIENT_ID',
            'client_secret_env': 'GITHUB_CLIENT_SECRET',
            'scopes': [
                'read:user',
                'user:email',
                'read:org',
                'repo',
            ],
            'auth_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
        },
    }

    def __init__(self, user_email: str = None):
        """
        Initialize OAuth manager.

        Args:
            user_email: User's email for per-user token storage.
                       If None, uses legacy global storage for backward compat.
        """
        self.user_email = user_email
        self.tokens = self._load_tokens()

    def _get_token_path(self, service: str = None) -> str:
        """Get the token storage path for the current user."""
        if self.user_email:
            # Per-user storage in oauth-tokens volume
            if service:
                return f"{TOKEN_STORAGE_BASE}/{self.user_email}/{service}.json"
            return f"{TOKEN_STORAGE_BASE}/{self.user_email}/tokens.json"
        else:
            # Legacy global storage for backward compatibility
            return "/home/claude/data/oauth_tokens.json"

    def _load_tokens(self) -> Dict[str, Any]:
        """Load stored tokens from file, supporting multiple formats."""
        tokens = {}

        if self.user_email:
            # Check for per-service token files (google.json, github.json, etc.)
            user_dir = f"{TOKEN_STORAGE_BASE}/{self.user_email}"
            if os.path.isdir(user_dir):
                for filename in os.listdir(user_dir):
                    if filename.endswith('.json'):
                        service_name = filename[:-5]  # Remove .json
                        filepath = os.path.join(user_dir, filename)
                        try:
                            with open(filepath, 'r') as f:
                                data = json.load(f)
                                # Handle web app format: {"provider": "...", "tokens": {...}}
                                if 'tokens' in data and isinstance(data['tokens'], dict):
                                    token_data = data['tokens'].copy()
                                    # Convert expires_at from epoch to ISO if needed
                                    if 'expires_at' in token_data and isinstance(token_data['expires_at'], (int, float)):
                                        token_data['expires_at'] = datetime.utcfromtimestamp(token_data['expires_at']).isoformat()
                                    tokens[service_name] = token_data
                                    # Google token works for gmail, calendar, contacts
                                    if service_name == 'google':
                                        tokens['gmail'] = token_data
                                        tokens['calendar'] = token_data
                                        tokens['contacts'] = token_data
                                else:
                                    # Direct format: {"access_token": ...}
                                    tokens[service_name] = data
                        except Exception as e:
                            print(f"Error loading token from {filepath}: {e}")

        # Also check legacy path
        legacy_path = "/home/claude/data/oauth_tokens.json"
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, 'r') as f:
                    legacy_tokens = json.load(f)
                    # Merge, preferring per-user tokens
                    for k, v in legacy_tokens.items():
                        if k not in tokens:
                            tokens[k] = v
            except Exception:
                pass

        return tokens

    def _save_tokens(self):
        """Save tokens to file."""
        token_path = self._get_token_path()
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as f:
            json.dump(self.tokens, f, indent=2)

    def get_token(self, service: str) -> Optional[str]:
        """
        Get access token for a service.
        Returns None if not authenticated or token is expired.
        """
        if service not in self.tokens:
            return None

        token_data = self.tokens[service]

        # Check expiration
        expires_at = token_data.get('expires_at')
        if expires_at:
            if datetime.fromisoformat(expires_at) < datetime.utcnow():
                # Token expired - try to refresh
                return self._refresh_token(service)

        return token_data.get('access_token')

    def _refresh_token(self, service: str) -> Optional[str]:
        """Refresh an expired token using the refresh token."""
        if service not in self.tokens:
            return None

        token_data = self.tokens[service]
        refresh_token = token_data.get('refresh_token')

        if not refresh_token:
            return None

        service_config = self.SERVICES.get(service)
        if not service_config:
            return None

        client_id = os.environ.get(service_config['client_id_env'])
        client_secret = os.environ.get(service_config['client_secret_env'])

        if not client_id or not client_secret:
            return None

        try:
            import httpx

            response = httpx.post(
                service_config['token_url'],
                data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                }
            )

            if response.status_code == 200:
                new_token_data = response.json()

                # Update stored token
                self.tokens[service]['access_token'] = new_token_data['access_token']
                if 'expires_in' in new_token_data:
                    expires_at = datetime.utcnow() + timedelta(seconds=new_token_data['expires_in'])
                    self.tokens[service]['expires_at'] = expires_at.isoformat()

                self._save_tokens()
                return new_token_data['access_token']
        except Exception as e:
            print(f"Error refreshing token for {service}: {e}")

        return None

    def store_token(self, service: str, token_data: Dict[str, Any]):
        """Store a new token after OAuth flow completes."""
        if 'expires_in' in token_data:
            expires_at = datetime.utcnow() + timedelta(seconds=token_data['expires_in'])
            token_data['expires_at'] = expires_at.isoformat()

        self.tokens[service] = token_data
        self._save_tokens()

    def is_authenticated(self, service: str) -> bool:
        """Check if we have a valid token for a service."""
        return self.get_token(service) is not None

    def get_auth_url(self, service: str, redirect_uri: str, state: str = None) -> Optional[str]:
        """
        Generate the OAuth authorization URL for a service.

        Args:
            service: Service name (gmail, calendar, linkedin)
            redirect_uri: Where to redirect after auth
            state: Optional state parameter for security

        Returns:
            Authorization URL to redirect user to
        """
        if service not in self.SERVICES:
            return None

        config = self.SERVICES[service]
        client_id = os.environ.get(config['client_id_env'])

        if not client_id:
            return None

        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(config['scopes']),
            'access_type': 'offline',  # For refresh tokens
            'prompt': 'consent',
        }

        if state:
            params['state'] = state

        query_string = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{config['auth_url']}?{query_string}"

    def exchange_code(self, service: str, code: str, redirect_uri: str) -> bool:
        """
        Exchange authorization code for tokens.

        Args:
            service: Service name
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in auth URL

        Returns:
            True if successful, False otherwise
        """
        if service not in self.SERVICES:
            return False

        config = self.SERVICES[service]
        client_id = os.environ.get(config['client_id_env'])
        client_secret = os.environ.get(config['client_secret_env'])

        if not client_id or not client_secret:
            return False

        try:
            import httpx

            response = httpx.post(
                config['token_url'],
                data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code',
                }
            )

            if response.status_code == 200:
                token_data = response.json()
                self.store_token(service, token_data)
                return True
            else:
                print(f"Token exchange failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error exchanging code for {service}: {e}")

        return False

    def revoke_token(self, service: str):
        """Revoke and remove token for a service."""
        if service in self.tokens:
            del self.tokens[service]
            self._save_tokens()

    def get_status(self) -> Dict[str, bool]:
        """Get authentication status for all services."""
        return {
            service: self.is_authenticated(service)
            for service in self.SERVICES
        }


# Cache of OAuth managers per user
_oauth_managers: Dict[str, OAuthManager] = {}


def get_oauth_manager(user_email: str = None) -> OAuthManager:
    """
    Get OAuth manager instance for a user.

    Args:
        user_email: User's email. If None, tries to auto-discover from tokens directory.
    """
    global _oauth_managers

    # Auto-discover user email if not provided
    if user_email is None:
        user_email = _discover_user_email()

    cache_key = user_email or "__global__"
    if cache_key not in _oauth_managers:
        _oauth_managers[cache_key] = OAuthManager(user_email)
    return _oauth_managers[cache_key]


def _discover_user_email() -> Optional[str]:
    """
    Try to discover user email from tokens directory.
    Returns the first user directory found, or None.
    """
    if os.path.isdir(TOKEN_STORAGE_BASE):
        for entry in os.listdir(TOKEN_STORAGE_BASE):
            entry_path = os.path.join(TOKEN_STORAGE_BASE, entry)
            if os.path.isdir(entry_path) and '@' in entry:
                return entry
    return None


def get_oauth_status(user_email: str = None) -> Dict[str, bool]:
    """Get OAuth status for all supported services."""
    return get_oauth_manager(user_email).get_status()


def initiate_oauth(service: str, redirect_uri: str, user_email: str = None) -> Optional[str]:
    """
    Start OAuth flow for a service.

    Returns the URL to redirect the user to, or None if service not supported.
    """
    return get_oauth_manager(user_email).get_auth_url(service, redirect_uri)
