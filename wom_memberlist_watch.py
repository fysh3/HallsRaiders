import os
import json
import hashlib
import requests
from typing import Set, List, Dict, Any

API_BASE = "https://api.wiseoldman.net/v2"
GROUP_ID = os.environ["WOM_GROUP_ID"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

STATE_FILE = "known_members.json"

def load_state_members() -> Set[str]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return set()

    members = data.get("members", [])
    out: Set[str] = set()

    for item in members:
        if isinstance(item, dict):
            u = item.get("username")
            if isinstance(u, str) and u.strip():
                out.add(u.strip())
        elif isinstance(item, str):
            u = item.strip()
            if u:
                out.add(u)

    return out

def save_state_members(members: Set[str]) -> None:
    payload = {"members": [{"username": u} for u in sorted(members, key=str.lower)]}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def fetch_current_members() -> Set[str]:
    r = requests.get(f"{API_BASE}/groups/{GROUP_ID}", timeout=30)
    r.raise_for_status()
    data: Dict[str, Any] = r.json()

    out: Set[str] = set()
    for m in data.get("memberships", []):
        player = m.get("player") or {}
        u = player.get("username")
        if isinstance(u, str) and u.strip():
            out.add(u.strip())
    return out

def post_discord(lines: List[str]) -> None:
    r = requests.post(DISCORD_WEBHOOK_URL, json={"content": "\n".join(lines)}, timeout=30)
    r.raise_for_status()

def short_hash(usernames: List[str]) -> str:
    h = hashlib.sha256("\n".join(usernames).encode("utf-8")).hexdigest()
    return h[:10]

def main() -> None:
    previous = load_state_members()
    current = fetch_current_members()

    # Baseline silently on first run
    if not previous:
        save_state_members(current)
        print(f"First run baseline saved: {len(current)} members.")
        return

    added = sorted(current - previous, key=str.lower)
    removed = sorted(previous - current, key=str.lower)

    if not added and not removed:
        print("No membership changes.")
        return

    snap = short_hash(sorted(list(current), key=str.lower))

    lines = [
        "🔔 **WOM group membership changed**",
        f"- Previous: **{len(previous)}** | Current: **{len(current)}**",
        f"- Snapshot: `{snap}`",
    ]
    if added:
        lines += ["", "✅ **Added:** " + ", ".join(added)]
    if removed:
        lines += ["", "❌ **Removed:** " + ", ".join(removed)]

    post_discord(lines)

    # Persist new state
    save_state_members(current)
    print(f"Saved updated membership list. Added={len(added)} Removed={len(removed)}")

if __name__ == "__main__":
    main()
