"""Render neofetch.svg: a phosphor-green terminal card with live GitHub stats."""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape

USER = "NightzDev"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = sys.argv[1] if len(sys.argv) > 1 else "neofetch.svg"

ART = r"""
   .-----------------------------.
   |  .-----------------------.  |
   |  | C:\> DIAL 555-0808    |  |
   |  | CONNECT 300           |  |
   |  |                       |  |
   |  | > ACCESS GRANTED      |  |
   |  | > root@node01:~#      |  |
   |  |                       |  |
   |  '-----------------------'  |
   |   NIGHTZ-TERM 80       o o  |
   '-----------------------------'
        __|_______________|__
      .'  :::::::::::::::::  '.
     /  :::::::::::::::::::::  \
    '---------------------------'
""".strip("\n").splitlines()

WIDTH = 46  # columns of the info panel, leader dots fill the gap


def api(path, body=None):
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def fetch_stats():
    try:
        user = api(f"/users/{USER}")
        repos = api(f"/users/{USER}/repos?per_page=100&type=owner")
        commits = api(f"/search/commits?q=author:{USER}&per_page=1")["total_count"]
    except Exception as exc:  # keep the card renderable without network
        print(f"stats unavailable: {exc}", file=sys.stderr)
        return None
    contributions = None
    if TOKEN:
        query = (
            "query($login:String!){user(login:$login){contributionsCollection"
            "{contributionCalendar{totalContributions}}}}"
        )
        try:
            res = api("/graphql", {"query": query, "variables": {"login": USER}})
            contributions = res["data"]["user"]["contributionsCollection"][
                "contributionCalendar"
            ]["totalContributions"]
        except Exception as exc:
            print(f"contributions unavailable: {exc}", file=sys.stderr)
    own = [r for r in repos if not r["fork"]]
    return {
        "created": datetime.fromisoformat(user["created_at"].replace("Z", "+00:00")),
        "repos": len(own),
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user["followers"],
        "commits": commits,
        "contributions": contributions,
    }


def uptime(created):
    now = datetime.now(timezone.utc)
    months = (now.year - created.year) * 12 + now.month - created.month
    if now.day < created.day:
        months -= 1
    years, months = divmod(months, 12)
    def plural(n, word):
        return f"{n} {word}" + ("" if n == 1 else "s")

    return f"{plural(years, 'year')}, {plural(months, 'month')}"


def row(key, value):
    dots = WIDTH - len(key) - len(value) - 2
    return [("key", key + " "), ("dot", "." * max(dots, 1) + " "), ("val", value)]


def build_lines(stats):
    def fmt(n):
        return "--" if n is None else f"{n:,}"

    up = uptime(stats["created"]) if stats else "--"
    s = stats or {}
    header = "nightzdev@node01"
    return [
        [("val", header)],
        [("dot", "-" * WIDTH)],
        row("OS", "BBS-DOS 6.22 / Linux"),
        row("Uptime", up),
        row("Host", "Yuri Harada"),
        row("Kernel", "Software Engineer"),
        row("Shell", "bash, 300 baud"),
        [],
        row("Languages.Code", "Python, Rust, Go, TS"),
        row("Languages.Also", "Java, Kotlin, Dart"),
        row("Languages.Real", "Portuguese, English"),
        [],
        row("Focus", "offensive & defensive sec"),
        row("Also", "recon, OS internals"),
        row("Hobby", "writing interpreters"),
        [],
        [("dot", "- GitHub Stats " + "-" * (WIDTH - 15))],
        row("Repos", fmt(s.get("repos"))),
        row("Stars", fmt(s.get("stars"))),
        row("Followers", fmt(s.get("followers"))),
        row("Commits", fmt(s.get("commits"))),
        row("Contributions (1y)", fmt(s.get("contributions"))),
    ]


def render(stats):
    lh, fs, pad = 20, 16, 28
    info = build_lines(stats)
    rows = max(len(ART), len(info)) + 2
    height = rows * lh + pad * 2
    width = 985
    art_x, info_x = pad, 390
    art_top = pad + lh * (1 + (len(info) - len(ART)) // 2)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="\'Courier New\',Courier,monospace" '
        f'font-size="{fs}px">',
        "<style>"
        ".art{fill:#00ff41}.key{fill:#00ff41}.val{fill:#b6ffc4}"
        ".dot{fill:#1a7f1a}.cur{fill:#00ff41}"
        "</style>",
        "<defs>"
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="2" fill="#000" opacity="0.35"/></pattern>'
        '<filter id="glow"><feGaussianBlur stdDeviation="1.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<radialGradient id="vig" cx="50%" cy="50%" r="75%">'
        '<stop offset="60%" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="100%" stop-color="#000" stop-opacity="0.75"/></radialGradient>'
        "</defs>",
        f'<rect width="{width}" height="{height}" rx="14" fill="#020a02"/>',
        '<g filter="url(#glow)">',
    ]

    out.append(f'<text x="{art_x}" y="{art_top}" class="art" xml:space="preserve">')
    for i, line in enumerate(ART):
        out.append(f'<tspan x="{art_x}" dy="{0 if i == 0 else lh}">{escape(line)}</tspan>')
    out.append("</text>")

    out.append(f'<text x="{info_x}" y="{pad + lh}" xml:space="preserve">')
    for i, parts in enumerate(info):
        dy = 0 if i == 0 else lh
        spans = "".join(f'<tspan class="{c}">{escape(t)}</tspan>' for c, t in parts) or " "
        out.append(f'<tspan x="{info_x}" dy="{dy}">{spans}</tspan>')
    out.append("</text>")

    prompt_y = pad + lh * (len(info) + 2)
    out.append(
        f'<text x="{info_x}" y="{prompt_y}" xml:space="preserve">'
        '<tspan class="key">nightzdev@node01</tspan><tspan class="val">:~$ </tspan>'
        '<tspan class="cur">█<animate attributeName="opacity" values="1;1;0;0" '
        'dur="1.1s" repeatCount="indefinite"/></tspan></text>'
    )
    out.append("</g>")
    out.append(f'<rect width="{width}" height="{height}" rx="14" fill="url(#scan)"/>')
    out.append(f'<rect width="{width}" height="{height}" rx="14" fill="url(#vig)"/>')
    out.append(
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" '
        'fill="none" stroke="#00ff41" stroke-opacity="0.5" stroke-width="2"/>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(fetch_stats()))
    print(f"wrote {OUT}")
