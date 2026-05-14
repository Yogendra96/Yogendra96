#!/usr/bin/env python3
import os
import re
import json
import base64
import urllib.request
from datetime import datetime, timezone

WAKA_API = "https://wakatime.com/api/v1"
README = "README.md"
GH_USER = "Yogendra96"


def waka_headers(api_key):
    auth = base64.b64encode(f"{api_key}:".encode()).decode()
    return {"Authorization": f"Basic {auth}"}


def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_wakatime(api_key):
    headers = waka_headers(api_key)
    stats = fetch_json(f"{WAKA_API}/users/current/stats/last_7_days", headers)
    data = stats.get("data", {})
    summaries = fetch_json(
        f"{WAKA_API}/users/current/summaries?range=last_7_days&timezone=Asia/Dubai",
        headers,
    )
    return data, summaries.get("data", [])


def fetch_github(token):
    headers = (
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        if token
        else {}
    )
    return fetch_json(f"https://api.github.com/users/{GH_USER}", headers)


def lang_bar(pct):
    filled = max(round(pct / 5), 0)
    return "█" * filled + "░" * (20 - filled)


def build_waka_block(stats, summaries):
    days = stats.get("days", [])
    total_secs = sum(d.get("total_seconds", 0) for d in days)
    hrs, rem = divmod(int(total_secs), 3600)
    mins = rem // 60
    num_days = max(len(days), 1)
    daily_avg = total_secs / num_days / 3600

    lines = ["```text"]
    lines.append(f"Total (7d): {hrs}h {mins}m  |  Daily avg: {daily_avg:.1f}h")
    lines.append("")

    langs = stats.get("languages", [])
    if langs:
        lines.append("Languages:")
        for l in langs[:6]:
            pct = l.get("percent", 0)
            lines.append(f"  {l['name']:<16} {lang_bar(pct)} {pct:.1f}%")

    editors = stats.get("editors", [])
    if editors:
        lines.append("")
        lines.append("Editors:")
        for e in editors[:3]:
            lines.append(f"  {e['name']:<12} {lang_bar(e.get('percent', 0))} {e.get('percent', 0):.1f}%")

    if summaries:
        lines.append("")
        lines.append("Daily Breakdown:")
        for day in summaries[-7:]:
            date = day.get("range", {}).get("date", "?")
            gt = day.get("grand_total", {})
            secs = gt.get("total_seconds", 0)
            h, r = divmod(int(secs), 3600)
            m = r // 60
            # show last 5 chars of date (MM-DD)
            label = date[-5:]
            bar_len = max(round(secs / 3600 * 2), 1)
            bar = "▓" * min(bar_len, 20)
            lines.append(f"  {label}  {bar}  {h}h{m}m")

    lines.append("```")
    return "\n".join(lines)


def build_gh_block(gh):
    if not gh:
        return ""
    total_repos = gh.get("public_repos", 0) + gh.get("total_private_repos", 0)
    return (
        f"  Repos: {total_repos}\n"
        f"  Followers: {gh.get('followers', 0)}\n"
        f"  Following: {gh.get('following', 0)}"
    )


def main():
    waka_key = os.environ.get("WAKATIME_API_KEY")
    gh_token = os.environ.get("GITHUB_TOKEN")

    if not waka_key:
        print("error: WAKATIME_API_KEY not set")
        return 1

    stats, summaries = fetch_wakatime(waka_key)
    gh = fetch_github(gh_token) if gh_token else {}

    waka_block = build_waka_block(stats, summaries)
    gh_block = build_gh_block(gh)

    with open(README) as f:
        readme = f.read()

    readme = re.sub(
        r"<!--START_SECTION:waka-->.*?<!--END_SECTION:waka-->",
        f"<!--START_SECTION:waka-->\n{waka_block}\n<!--END_SECTION:waka-->",
        readme,
        flags=re.DOTALL,
    )

    now = datetime.now(timezone.utc).strftime("%B %Y")
    readme = re.sub(r"Last updated: \w+ \d{4}", f"Last updated: {now}", readme)

    with open(README, "w") as f:
        f.write(readme)

    print("README updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
