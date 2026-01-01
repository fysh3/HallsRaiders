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
    Try multiple WOM group endpoints and extract usernames.
    """
    urls = [
        f"ht
