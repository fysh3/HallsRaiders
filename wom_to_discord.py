import os
import json
import requests

GROUP_ID = os.environ["WOM_GROUP_ID"]
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = "known_members.json"

def load_known_members():
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        return set(x["username"] for x in data.get("members", []))
    except FileNotFoundError:
        return set()

def save_known_members(members):
    with open(STATE_FILE, "w") as f:
        json.dump(
            {"members": [{"username": m} for m in sorted(members)]},
            f,
            indent=2
        )

def fetch_current_members():
    url = "https://api.wiseoldman.net/v2/groups/" + GROUP_ID
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    members = set()
    for m in data.get("memberships", []):
        player = m.get("player", {})
        username = player.get("username")
        if username:
            members.add(username)

    return members

def post_welcome(new_members):
    if not new_members:
        return

    message = "🎉 **Welcome to the clan!** 🎉\n\n"
    for name in new_members:
        message += "👋 **" + name + "**\n"

    requests.post(WEBHOOK_URL, json={"content": message}, timeout=30)

def main():
    known = load_known_members()
    current = fetch_current_members()

    if not known:
        save_known_members(current)
        return

    new_members = current - known
    post_welcome(sorted(new_members))
    save_known_members(current)

if __name__ == "__main__":
    main()
