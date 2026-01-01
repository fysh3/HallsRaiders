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
    url = f"https://api.wiseoldman.net/v2/groups/{GROUP_ID}/members"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return set(m["username"] for m in r.json())

def post_welcome(new_members):
    if not new_members:
        return

    lines = ["🎉 **Welcome to the clan!** 🎉", ""]
    for name in new_members:
        lines.append(f"👋 **{name}**")

    requests.post(WEBHOOK_URL, json={"content": "\n".join(lines)}, timeout=30)

def main():
    known = load_known()
    current = fetch_current_members()

    new_members = sorted(current - known, key=str.lower)

    # First run: initialize without posting
    if not known:
        save_known(current)
        return

    post_welcome(new_members)
    save_known(current)

if __name__ == "__main__":
    main()
