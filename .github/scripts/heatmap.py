"""Genera dist/heatmap.svg: calendario de contribuciones con la paleta de la terminal."""
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

USER = os.environ.get("GH_USER", "Beardynh")
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""

BG, LINE, TEXT, SUB = "#0e0c10", "#4a3f45", "#e6dccb", "#8d8496"
LEVELS = ["#1f1a20", "#6b2636", "#9e2d42", "#c9344b", "#e23a52"]
MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
FONT = "'JetBrains Mono', 'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

W, PAD, CELL, STEP = 920, 48, 11, 14


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(n, peak):
    if n == 0:
        return 0
    # Escala raíz: con pocos días muy activos, el resto no queda casi invisible.
    return min(4, 1 + int(3 * (n / max(peak, 1)) ** 0.5))


def render(cal):
    weeks = cal["weeks"]
    peak = max(d["contributionCount"] for w in weeks for d in w["contributionDays"])
    x0, y0 = PAD + 40, 112
    parts = []

    last_month = None
    for wi, week in enumerate(weeks):
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month:
            # Evita una etiqueta de mes pegada a la siguiente en los bordes.
            if 0 < wi < len(weeks) - 2:
                parts.append(f'<text x="{x0 + wi * STEP}" y="{y0 - 12}" class="s">{MONTHS[first.month - 1]}</text>')
            last_month = first.month
        for d in week["contributionDays"]:
            wd = (date.fromisoformat(d["date"]).weekday() + 1) % 7  # domingo = 0
            n = d["contributionCount"]
            parts.append(
                f'<rect x="{x0 + wi * STEP}" y="{y0 + wd * STEP}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{LEVELS[level(n, peak)]}"><title>{d["date"]}: {n}</title></rect>'
            )
    for wd, label in ((1, "lun"), (3, "mié"), (5, "vie")):
        parts.append(f'<text x="{x0 - 10}" y="{y0 + wd * STEP + 10}" class="s" text-anchor="end">{label}</text>')

    foot = y0 + 7 * STEP + 30
    total = cal["totalContributions"]
    parts.append(f'<text x="{x0}" y="{foot}" class="s"><tspan fill="{TEXT}">{total}</tspan> en el último año</text>')
    legend_x = x0 + len(weeks) * STEP - 5 * STEP - 30
    parts.append(f'<text x="{legend_x - 10}" y="{foot}" class="s" text-anchor="end">menos</text>')
    for i, col in enumerate(LEVELS):
        parts.append(f'<rect x="{legend_x + i * STEP}" y="{foot - 10}" width="{CELL}" height="{CELL}" rx="2.5" fill="{col}"/>')
    parts.append(f'<text x="{legend_x + 5 * STEP + 6}" y="{foot}" class="s">más</text>')

    H = foot + 36
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>
    text {{ font-family: {FONT}; }}
    .s {{ font-size: 13px; fill: {SUB}; }}
  </style>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{BG}" stroke="{LINE}"/>
  <text x="{PAD}" y="52" font-size="17" fill="{SUB}"><tspan fill="#3fd1c7">~</tspan> <tspan fill="#e23a52">❯</tspan> git log --since="1 year ago"</text>
  {"".join(parts)}
</svg>
"""


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/heatmap.svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(fetch()), encoding="utf-8")
    print(f"wrote {out}")
