import os
import requests
from datetime import datetime, timezone

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
GROUP_ID = os.environ["WOM_GROUP_ID"]

METRIC = os.getenv("WOM_METRIC", "overall")   # overall = total XP
PERIOD = os.getenv("WOM_PERIOD", "day")       # day/week/month
LIMIT = int(os.getenv("WOM_LIMIT", "5"))      # top N members

def get_group_gains(group_id: str, metric: str, period: str, limit: int):
    url = f"https://api.wiseoldman.net/v2/groups/{group_id}/gained"
    r = requests.get(url, params={"metric": metric, "period": period, "limit": limit}, timeout=30)
    r.raise_for_status()
    return r.json()

def post_to_discord(content: str):
    r = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=30)
    r.raise_for_status()

def fmt_num(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)

def main():
    rows = get_group_gains(GROUP_ID, METRIC, PERIOD, LIMIT)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [f"**WOM Clan Update** ({PERIOD}) — metric: **{METRIC}** — {now}"]

    if not rows:
        lines.append("_No results returned (group might be untracked or no activity)._")
    else:
        for i, entry in enumerate(rows, start=1):
            player = entry.get("player", {})
            name = player.get("displayName") or player.get("username") or "Unknown"
            gained = entry.get("gained", 0)
            lines.append(f"{i}. **{name}**: +{fmt_num(gained)}")

    post_to_discord("\n".join(lines))

if __name__ == "__main__":
    main()
