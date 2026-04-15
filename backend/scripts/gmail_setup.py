#!/usr/bin/env python3
"""
One-time script to obtain a Gmail OAuth2 refresh token.

Usage:
  1. Create OAuth2 credentials at https://console.cloud.google.com/
     - Application type: Desktop app
     - Enable Gmail API
  2. Download credentials JSON and set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env
  3. Run: python scripts/gmail_setup.py
  4. Follow the browser auth flow
  5. Copy the printed refresh token to your .env as GMAIL_REFRESH_TOKEN
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_SECRETS = {
    "installed": {
        "client_id": os.getenv("GMAIL_CLIENT_ID", ""),
        "client_secret": os.getenv("GMAIL_CLIENT_SECRET", ""),
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    if not CLIENT_SECRETS["installed"]["client_id"]:
        print("ERROR: Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables first.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_config(CLIENT_SECRETS, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n✅ Success! Add this to your .env file:\n")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("\nKeep this token secret — it grants send access to your Gmail account.")


if __name__ == "__main__":
    main()
