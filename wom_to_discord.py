import os
import json
import time
import requests

GROUP_ID = os.environ["WOM_GROUP_ID"]
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
VERIFICATION_CODE = os.environ.get("WOM_VERIFICATION_CODE", "").strip()

STATE_FILE = "known_members.json"


def load_known_members():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(x["username"] for x in data.get("members", []))
    except FileNotFoundError:
        return set()


def save_known_members(members):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"members": [{"username": m} for m in sorted(members, key=str.lower)]}, f, indent=2)


def wom_update_all():
    """
    Requests WOM to update outdated members' stats.
    Requires verification code: POST /v2/groups/:id/update-all
    """
    if not VERIFICATION_CODE:
        print("WOM_VERIFICATION_CODE not set; skipping WOM update-all request.")
        return

    url = "https://api.wiseoldman.net/v2/groups/" + GROUP_ID + "/update-all"
    payload = {"verificationCode": VERIFICATION_CODE}

    r = requests.post(url, json=payload, timeout=30)
    # If this fails, don't hard-fail the whole workflow — we can still check membership.
    if r.status_code >= 400:
        print("WOM update-all request failed:", r.status_code, r.text[:300])
        return

    try:
        print("WOM update-all response:", r.json())
    except Exception:
        print("WOM update-all response (non-json):", r.text[:300])


def fetch_current_members():
    """
    Group details endpoint: GET /v2/groups/:id
    Returns memberships with player.username.
    """
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

    msg = "🎉 **Welcome to the clan!** 🎉\n\n"
    for name in new_members:
        msg += "👋 **" + name + "**\n"

    r = requests.post(WEBHOOK_URL, json={"content": msg}, timeout=30)
    r.raise_for_status()


def main():
    # 1) Ask WOM to update first
    wom_update_all()

    # 2) Give WOM a moment (small delay; update queue can take longer, but this helps)
    time.sleep(20)

    # 3) Compare member list with last run
    known = load_known_members()
    current = fetch_current_members()

    print("Known members:", len(known))
    print("Current members:", len(current))

    # First run: initialize without posting
    if not known:
        print("First run: initializing known_members.json (no post).")
        save_known_members(current)
        return

    new_members = sorted(current - known, key=str.lower)
    print("New members detected:", new_members)

    # Only post if new members exist
    if new_members:
        post_welcome(new_members)

    # Update state
    save_known_members(current)


if __name__ == "__main__":
    main()
