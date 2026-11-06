#!/usr/bin/env python3
"""Download the four current ServiceNow report workbooks from UT System OneDrive via Microsoft Graph."""
from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import quote
import msal
import requests

FILES = [
    "PMO Daily Roadmunk - Projects.xlsx",
    "PMO Daily Roadmunk - Demands.xlsx",
    "PMO Daily Roadmunk - Enhancements.xlsx",
    "PMO Daily Roadmunk - Ideas.xlsx",
]

def need(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable/secret: {name}")
    return value

def main() -> None:
    tenant = need("MS_TENANT_ID")
    client = need("MS_CLIENT_ID")
    secret = need("MS_CLIENT_SECRET")
    user = need("ONEDRIVE_USER")
    folder = os.getenv("ONEDRIVE_FOLDER", "SIS Roadmap/Current").strip("/")
    output = Path(os.getenv("ROADMAP_SOURCE_DIR", "roadmap_sources"))
    output.mkdir(parents=True, exist_ok=True)

    app = msal.ConfidentialClientApplication(
        client_id=client,
        client_credential=secret,
        authority=f"https://login.microsoftonline.com/{tenant}",
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    token = result.get("access_token")
    if not token:
        raise SystemExit(f"Microsoft authentication failed: {result.get('error_description', result)}")

    headers = {"Authorization": f"Bearer {token}"}
    for filename in FILES:
        # Graph path-addressing requires each path segment encoded, while preserving slashes.
        cloud_path = "/".join(quote(seg, safe="") for seg in f"{folder}/{filename}".split("/"))
        url = f"https://graph.microsoft.com/v1.0/users/{quote(user, safe='@.')}/drive/root:/{cloud_path}:/content"
        response = requests.get(url, headers=headers, timeout=120, allow_redirects=True)
        if response.status_code != 200:
            raise SystemExit(f"Download failed for {filename}: HTTP {response.status_code} - {response.text[:500]}")
        target = output / filename
        target.write_bytes(response.content)
        if target.stat().st_size < 1000:
            raise SystemExit(f"Downloaded file is suspiciously small: {filename} ({target.stat().st_size} bytes)")
        print(f"Downloaded {filename}: {target.stat().st_size:,} bytes")

if __name__ == "__main__":
    main()
