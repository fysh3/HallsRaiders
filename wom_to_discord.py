import os
import json
import requests

GROUP_ID = os.environ["WOM_GROUP_ID"]
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

STATE_FILE = "known_members.json"

def load_known():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(m["username"] for m in data.get("members", []))
    except FileNotFoundError:
        return set()

def save_known(members):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"members": [{"username": m} for m in sorted(members, key=str.lower)]},
            f,
            indent=2
        )

def fetch_current_members():
    """
    WOM group membership endpoints have changed across versions.
    This tries a couple of known patterns and extracts usernames safely.
    """
    candidates = [
        f"https://api.wiseoldman.net/v2/groups/{GROUP_ID}",          # group details (often includes memberships)
        f"https://api.wiseoldman.net/v2/groups/{GROUP_ID}/members",  # some deployments had this
    ]

    last_error = None

    for url in candidates:
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 404:
                last_error = f"404 at {url}"
                continue
            r.raise_for_status()
            data = r.json()

            # Pattern A: data has "memberships": [ { "player": { "username": ... } } ]
            if isinstance(data, dict) and "memberships" in data and isinstance(data["memberships"], list):
                usernames = set()
                for m in data["memberships"]:
                    player = (m or {}).get("player") or {}
                    u = player.get("username")
                    if u:
                        usernames.add(u)
                if usernames:
                    return usernames

            # Pattern B: data has "members": [ { "username": ... } ] or similar
            if isinstance(data, dict) and "members" in data and isinstance(data["members"], list):
                usernames = set()
                for m in data["members"]:
                    u = (m or {}).get("username") or (m or {}).get("displayName")
                    if u:
                        usernames.add(u)
                if usernames:
                    return usernames

            # Pattern C: endpoint returns a list directly
            if isinstance(data, list):
                usernames = set()
                for m in data:
                    u = (m or {}).get("username") or (m or {}).get("displayName")
                    if u:
                        usernames.add(u)
                if usernames:
                    return usernames

            # If we got here, the endpoint worked but structure is unexpected
            raise RuntimeError(f"Unexpected response shape from {url}: keys={list(data.keys()) if isinstance(data, dict) else type(data)}")

        except Exception as e:
            last_error = str(e)

    raise RuntimeError(
        "Could not fetch members. "
        "Likel
