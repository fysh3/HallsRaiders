import os
import json
import datetime as dt
import requests

API_BASE = "https://api.wiseoldman.net/v2"

GROUP_ID = os.environ["WOM_GROUP_ID"]
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

STATE_FILE = "weekly_gains_state.json"

# How many people to show
TOP_N = int(os.getenv("TOP_N", "10"))

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"last_posted_week": ""}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)

def post_to_discord(content: str):
    r = requests.post(WEBHOOK_URL, json={"content": content}, timeout=30)
    r.raise_for_status()

def iso_week_key_utc(now: dt.datetime) -> str:
    # Example: "2026-W01"
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

def fetch_group_weekly_gains():
    # Group Gains endpoint supports metric + period and limit :contentReference[oaicite:1]{index=1}
    params = {
        "metric": "overall",
        "period": "week",
        "limit": TOP_N
    }
    r = requests.get(f"{API_BASE}/groups/{GROUP_ID}/gained", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def format_xp(x: int) -> str:
    # 12345678 -> "12.35M", 123456 -> "123.46K"
    if x >= 1_000_000:
        return f"{x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{x/1_000:.2f}K"
    return str(x)

def main():
    now = dt.datetime.utcnow()
    week_key = iso_week_key_utc(now)

    state = load_state()
    if state.get("last_posted_week") == week_key:
        print(f"Already posted for {week_key}. Skipping.")
        return

    rows = fetch_group_weekly_gains()

    # Each entry is a DeltaLeaderboardEntry (player + gained value) :contentReference[oaicite:2]{index=2}
    if not rows:
        print("No gains returned.")
        return

    lines = [f"📊 **Weekly Top XP Gained** ({week_key}) — Top {min(TOP_N, len(rows))}"]
    for i, entry in enumerate(rows[:TOP_N], start=1):
        player = entry.get("player", {}) or {}
        name = player.get("displayName") or player.get("username") or "Unknown"
        gained = entry.get("gained", 0)
        try:
            gained_int = int(gained)
        except Exception:
            gained_int = 0
        lines.append(f"**{i}.** {name} — **{format_xp(gained_int)} XP**")

    post_to_discord("\n".join(lines))

    state["last_posted_week"] = week_key
    save_state(state)
    print(f"Posted weekly gains for {week_key}.")

if __name__ == "__main__":
    main()
