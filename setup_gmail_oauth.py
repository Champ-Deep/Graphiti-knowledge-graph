#!/usr/bin/env python3
"""
Gmail OAuth Setup Script

This script helps you obtain OAuth refresh tokens for Gmail API access.
Run this script once to authorize access and get your refresh token.

The OAuth client id and secret are read from GOOGLE_CLIENT_ID and
GOOGLE_CLIENT_SECRET, or from the JSON file at GOOGLE_CLIENT_SECRETS_FILE.
"""
import os
import sys

from dotenv import load_dotenv

from config.google_oauth import GoogleOAuthConfigError, load_google_oauth_client

# Gmail API scope - read-only access to emails
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.metadata',
]


def require_oauth_client() -> tuple[str, str]:
    """Load the OAuth client or exit with a message naming what to set."""
    load_dotenv()
    try:
        return load_google_oauth_client()
    except GoogleOAuthConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)


def get_credentials(client_id: str, client_secret: str):
    """Run OAuth flow and return credentials"""
    from google_auth_oauthlib.flow import InstalledAppFlow

    # Create client config from environment-provided credentials.
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/", "urn:ietf:wg:oauth:2.0:oob"]
        }
    }

    # Run the OAuth flow
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    print("\n" + "=" * 60)
    print("Gmail OAuth Authorization")
    print("=" * 60)
    print("\nA browser window will open for you to authorize access.")
    print("Please sign in with your Google Workspace account.\n")

    # This will open a browser for authorization
    credentials = flow.run_local_server(
        port=8080,
        prompt='consent',
        access_type='offline'  # This ensures we get a refresh token
    )

    return credentials


def test_gmail_access(credentials):
    """Test that we can access Gmail"""
    from googleapiclient.discovery import build

    print("\nTesting Gmail access...")

    service = build('gmail', 'v1', credentials=credentials)

    # Get user profile
    profile = service.users().getProfile(userId='me').execute()
    email = profile.get('emailAddress')
    print(f"Successfully connected to: {email}")

    # Get recent messages count
    messages = service.users().messages().list(userId='me', maxResults=5).execute()
    count = messages.get('resultSizeEstimate', 0)
    print(f"Total messages in inbox: ~{count}")

    return email


def save_credentials(credentials, email: str, client_id: str, client_secret: str) -> None:
    """Save credentials to .env file"""
    import re

    env_path = os.path.join(os.path.dirname(__file__), '.env')

    # Read existing .env
    env_content = ""
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_content = f.read()

    # Update Google credentials from the values already loaded for this run.
    updates = {
        'GOOGLE_CLIENT_ID': client_id,
        'GOOGLE_CLIENT_SECRET': client_secret,
        'GOOGLE_REFRESH_TOKEN': credentials.refresh_token,
        'GOOGLE_USER_EMAIL': email,
    }

    for key, value in updates.items():
        pattern = rf'^{key}=.*$'
        replacement = f'{key}={value}'

        if re.search(pattern, env_content, re.MULTILINE):
            env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
        else:
            env_content += f'\n{key}={value}'

    with open(env_path, 'w') as f:
        f.write(env_content)

    print(f"\nCredentials saved to {env_path}")


def main() -> None:
    client_id, client_secret = require_oauth_client()

    print("\n" + "=" * 60)
    print("Gmail OAuth Setup for CHAMP Graph")
    print("=" * 60)

    try:
        # Get OAuth credentials
        credentials = get_credentials(client_id, client_secret)

        if not credentials.refresh_token:
            print("\n[WARNING] No refresh token received!")
            print("This can happen if you've already authorized this app.")
            print("Try revoking access at https://myaccount.google.com/permissions")
            print("Then run this script again.")
            return

        # Test access
        email = test_gmail_access(credentials)

        # Save to .env
        save_credentials(credentials, email, client_id, client_secret)

        print("\n" + "=" * 60)
        print("SUCCESS! Gmail OAuth setup complete.")
        print("=" * 60)
        print("\nYour refresh token has been saved to .env")
        print(f"Connected email: {email}")
        print("\nYou can now run the email sync scripts!")
        print("\nNext steps:")
        print("1. Add your target accounts to config/accounts.py")
        print("2. Set TEAM_DOMAINS in .env to your company domain")
        print("3. Run: python sync_emails.py")

    except Exception as e:
        print(f"\n[ERROR] OAuth setup failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
