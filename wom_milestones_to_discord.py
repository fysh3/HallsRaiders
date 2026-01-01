import os
import json
import time
import requests
from typing import Dict, Any, List

API_BASE = "https://api.wiseoldman.net/v2"

GROUP_ID = os.environ["WOM_GROUP_ID"]
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

# Optional: limit which skills you announce (comma-separated)
# Examples:
#   SKILLS=overall
#   SKILLS=attack,strength,defence,hitpoints,ranged,magic,prayer
#   SKILLS=all  (default)
SKILLS_ENV = os.getenv("WOM_SKILLS", "all").strip().lower()

STATE_LEVELS_FILE = "known_levels.json"

# Simple rate limit so we don't hammer the API
REQUEST_SLEEP_SECONDS = float(os.getenv("WOM_REQUEST_SLEEP", "0.15"))

def load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

def post_to_discord(content: str) -> None:
    r = requests.post(WEBHOOK_URL, json={"content": content}, timeout=30)
    r.raise_for_status()

def get_group_members() -> List[str]:
    # Group Details includes memberships -> player -> username :contentReference[oaicite:2]{index=2}
    r = requests.get(f"{API_BASE}/groups/{GROUP_ID}", timeout=30)
    r.raise_for_status()
    data = r.json()
    usernames = []
    for m in data.get("memberships", []):
        p = m.get("player", {})
        u = p.get("username")
        if u:
            usernames.append(u)
    # de-dupe, keep stable order
    seen = set()
    out = []
    for u in usernames:
        key = u.lower()
        if key not in seen:
            seen.add(key)
            out.append(u)
    return out

def get_player_levels(username: str) -> Dict[str, int]:
    r = requests.get(f"{API_BASE}/players/{username}", timeout=30)
    r.raise_for_status()
    details = r.json()

    snap = details.get("latestSnapshot", {}) or {}
    skills = (snap.get("data", {}) or {}).get("skills", {}) or {}

    levels: Dict[str, int] = {}
    for skill_name, skill_obj in skills.items():
        lvl = skill_obj.get("level")
        if isinstance(lvl, int):
            levels[skill_name] = lvl
    return levels

def filter_skills(all_levels: Dict[str, int]) -> Dict[str, int]:
    if SKILLS_ENV in ("all", "", "everything"):
        return all_levels
    wanted = [s.strip().lower() for s in SKILLS_ENV.split(",") if s.strip()]
    wanted_set = set(wanted)
    return {k: v for k, v in all_levels.items() if k.lower() in wanted_set}

def main() -> None:
    levels_state: Dict[str, Dict[str, int]] = load_json(STATE_LEVELS_FILE, {})

    members = get_group_members()
    print(f"Members to check: {len(members)}")

    announcements = []

    for username in members:
        time.sleep(REQUEST_SLEEP_SECONDS)

        try:
            current_levels_all = get_player_levels(username)
        except requests.HTTPError as e:
            print(f"Skipping {username}: {e}")
            continue

        current_levels = filter_skills(current_levels_all)

        key = username.lower()
        prev_levels = levels_state.get(key)

        # First time seeing this player -> save baseline, no post
        if not isinstance(prev_levels, dict):
            levels_state[key] = current_levels
            continue

        # Detect increases
        changes = []
        for skill, new_lvl in current_levels.items():
            old_lvl = prev_levels.get(skill)
            if isinstance(old_lvl, int) and new_lvl > old_lvl:
                changes.append((skill, old_lvl, new_lvl))

        if changes:
            # Update stored levels
            for skill, _, new_lvl in changes:
                prev_levels[skill] = new_lvl

            # Build message (one message per player per run)
            changes_str = ", ".join([f"{skill} {old}->{new}" for (skill, old, new) in changes])
            announcements.append(f"🎉 **{username}** leveled up! {changes_str}")

        levels_state[key] = prev_levels

    # Save state
    save_json(STATE_LEVELS_FILE, levels_state)

    # Post announcements (avoid spam: batch up to ~10 lines/message)
    if announcements:
        chunk = []
        for line in announcements:
            chunk.append(line)
            if len(chunk) >= 10:
                post_to_discord("\n".join(chunk))
                chunk = []
        if chunk:
            post_to_discord("\n".join(chunk))
        print(f"Posted {len(announcements)} level-up announcements.")
    else:
        print("No level-ups detected.")

if __name__ == "__main__":
    main()
