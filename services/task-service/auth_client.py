import os
import requests

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:5001").rstrip("/")

def require_user(authorization_header: str) -> dict:
    # Validates token by calling auth-service /me
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise ValueError("Missing Bearer token")
    resp = requests.get(
        AUTH_SERVICE_URL + "/me",
        headers={"Authorization": authorization_header},
        timeout=10,
    )
    if resp.status_code != 200:
        raise ValueError("Invalid token")
    return resp.json()["user"]
