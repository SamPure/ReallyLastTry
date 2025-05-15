import streamlit as st
import hashlib
import os
from typing import Optional
import json
from datetime import datetime, timedelta

class DashboardAuth:
    def __init__(self, secrets_file: str = ".streamlit/secrets.toml"):
        """Initialize the authentication system."""
        self.secrets_file = secrets_file
        self._ensure_secrets_file()
        self._load_secrets()

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
        """Authenticate a user."""
        if username not in self.secrets["credentials"]["usernames"]:
            return False

        stored_hash = self.secrets["credentials"]["usernames"][username]["password"]
        return self._hash_password(password) == stored_hash

    def login(self) -> Optional[str]:
        """Handle the login process."""
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
            st.session_state.username = None

        if not st.session_state.authenticated:
            st.title("Dashboard Login")

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

        return st.session_state.username

    def logout(self):
        """Handle the logout process."""
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
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
