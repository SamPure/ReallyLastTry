import streamlit as st
import hashlib
import os
from typing import Optional, Dict, Any
import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import google.oauth2.credentials
import google_auth_oauthlib.flow
import google.auth.transport.requests
import requests
from pathlib import Path

class DashboardAuth:
    def __init__(self, secrets_file: str = ".streamlit/secrets.toml"):
        """Initialize the authentication system."""
        self.secrets_file = secrets_file
        self._ensure_secrets_file()
        self._load_secrets()
        self._init_oauth()

    def _init_oauth(self):
        """Initialize OAuth configuration."""
        self.oauth_config = {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8501"],
                "javascript_origins": ["http://localhost:8501"]
            }
        }

        # Save OAuth config to file for google_auth_oauthlib
        oauth_config_path = Path(".streamlit/oauth_config.json")
        oauth_config_path.parent.mkdir(exist_ok=True)
        with open(oauth_config_path, "w") as f:
            json.dump(self.oauth_config, f)

    def _ensure_secrets_file(self):
        """Ensure the secrets file exists with default credentials."""
        os.makedirs(os.path.dirname(self.secrets_file), exist_ok=True)
        if not os.path.exists(self.secrets_file):
            default_credentials = {
                "credentials": {
                    "usernames": {
                        "admin": {
                            "email": "admin@example.com",
                            "name": "Admin User",
                            "password": self._hash_password("admin")  # Change this in production
                        }
                    }
                }
            }
            with open(self.secrets_file, "w") as f:
                json.dump(default_credentials, f, indent=2)

    def _load_secrets(self):
        """Load secrets from the secrets file."""
        try:
            with open(self.secrets_file, "r") as f:
                self.secrets = json.load(f)
        except Exception as e:
            st.error(f"Failed to load secrets: {str(e)}")
            self.secrets = {"credentials": {"usernames": {}}}

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user with username/password."""
        if username not in self.secrets["credentials"]["usernames"]:
            return False

        stored_hash = self.secrets["credentials"]["usernames"][username]["password"]
        return self._hash_password(password) == stored_hash

    def authenticate_oauth(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate a user with OAuth credentials."""
        try:
            # Verify the token with Google
            response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {credentials['token']}"}
            )
            if response.status_code == 200:
                user_info = response.json()
                email = user_info.get("email")

                # Check if email is in allowed domains
                allowed_domains = os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",")
                if not allowed_domains or any(email.endswith(domain) for domain in allowed_domains):
                    return True
            return False
        except Exception as e:
            st.error(f"OAuth authentication failed: {str(e)}")
            return False

    def login(self) -> Optional[str]:
        """Handle the login process."""
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.oauth_credentials = None

        if not st.session_state.authenticated:
            st.title("Dashboard Login")

            # OAuth login
            if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
                if st.button("Sign in with Google"):
                    flow = google_auth_oauthlib.flow.Flow.from_client_config(
                        self.oauth_config,
                        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"]
                    )
                    flow.redirect_uri = "http://localhost:8501"

                    authorization_url, state = flow.authorization_url(
                        access_type="offline",
                        include_granted_scopes="true"
                    )

                    st.markdown(f'<a href="{authorization_url}" target="_self">Click here to authenticate with Google</a>', unsafe_allow_html=True)

                    # Handle OAuth callback
                    if "code" in st.experimental_get_query_params():
                        flow.fetch_token(
                            authorization_response=st.experimental_get_query_params()["code"][0]
                        )
                        credentials = flow.credentials

                        if self.authenticate_oauth(credentials):
                            st.session_state.authenticated = True
                            st.session_state.oauth_credentials = credentials
                            st.success("Google authentication successful!")
                            st.experimental_rerun()
                        else:
                            st.error("Google authentication failed. Please try again.")

            # Traditional login
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")

                if submit:
                    if self.authenticate(username, password):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.success("Login successful!")
                        st.experimental_rerun()
                    else:
                        st.error("Invalid username or password")

            return None

        return st.session_state.username or "OAuth User"

    def logout(self):
        """Handle the logout process."""
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.oauth_credentials = None
            st.experimental_rerun()

    def require_auth(self):
        """Decorator to require authentication for a function."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                username = self.login()
                if username is None:
                    return
                return func(*args, **kwargs)
            return wrapper
        return decorator
