"""Genera dark_mode.svg y light_mode.svg para el README de perfil de GitHub.

Uso:
    python generate.py                  # usa datos de config.json
    GITHUB_TOKEN=xxx python generate.py # además trae stats reales de GitHub
"""
import json
import os
import urllib.request
from datetime import date
from html import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
ASCII = open(os.path.join(ROOT, "ascii.txt"), encoding="utf-8").read().splitlines()

WIDTH = 60          # ancho en caracteres de la columna de datos
LINE_H = 20         # alto de línea en px
FONT = 16

THEMES = {
    "dark":  {"bg": "#161b22", "text": "#c9d1d9", "key": "#ff7b39", "dots": "#616e7f",
              "art": "#c9d1d9", "add": "#3fb950", "del": "#f85149"},
    "light": {"bg": "#f6f8fa", "text": "#24292f", "key": "#cf4a0e", "dots": "#9ba3ad",
              "art": "#24292f", "add": "#1a7f37", "del": "#cf222e"},
}


def uptime(birth: str) -> str:
    b = date.fromisoformat(birth)
    t = date.today()
    y, m, d = t.year - b.year, t.month - b.month, t.day - b.day
    if d < 0:
        m -= 1
        prev = (t.replace(day=1) - date.resolution)
        d += prev.day
    if m < 0:
        y -= 1
        m += 12
    return f"{y} años, {m} meses, {d} días"


def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req))["data"]


def github_stats(user: str):
    token = os.environ.get("GITHUB_TOKEN")
    placeholder = {"repos": "0", "stars": "0", "commits": "0", "followers": "0"}
    if not token:
        return placeholder
    q = """query($login:String!){ user(login:$login){
        followers{totalCount}
        repositories(ownerAffiliations:OWNER, first:100){ totalCount nodes{ stargazerCount } }
        contributionsCollection{ totalCommitContributions restrictedContributionsCount }
    }}"""
    try:
        u = gql(q, {"login": user}, token)["user"]
    except Exception as e:  # sin red o token inválido: no rompe el build
        print("No pude traer stats:", e)
        return placeholder
    cc = u["contributionsCollection"]
    return {
        "repos": f"{u['repositories']['totalCount']}",
        "stars": f"{sum(n['stargazerCount'] for n in u['repositories']['nodes'])}",
        "commits": f"{cc['totalCommitContributions'] + cc['restrictedContributionsCount']:,}",
        "followers": f"{u['followers']['totalCount']}",
    }


def row(key, value, width=WIDTH):
    """'. Key: ......... value' alineado a la derecha."""
    dots = width - len(key) - len(value) - 5
    return [("dots", ". "), ("key", key), ("text", ":"),
            ("dots", " " + "." * max(dots, 1) + " "), ("text", value)]


def pair_row(k1, v1, k2, v2):
    half = (WIDTH - 3) // 2 - 1
    left = row(k1, v1, half + 2)
    right = row(k2, v2, WIDTH - half - 3)[1:]  # ancho total = WIDTH  # sin el ". " inicial
    return left + [("text", " | ")] + right


def header(title):
    return [("text", "- " + title + " "), ("dots", "—" * (WIDTH - len(title) - 3))]


def build_lines(stats):
    lines = [[("key", CFG["handle"]), ("text", " "), ("dots", "—" * (WIDTH - len(CFG["handle"]) - 1))]]
    for i, sec in enumerate(CFG["sections"]):
        if i:
            lines.append([("dots", ".")])
        if isinstance(sec, dict):
            lines.append(header(sec["title"]))
            if sec["rows"] == "{stats}":
                lines.append(pair_row("Repos", stats["repos"], "Estrellas", stats["stars"]))
                lines.append(pair_row("Commits", stats["commits"], "Seguidores", stats["followers"]))
                continue
            sec = sec["rows"]
        for k, v in sec:
            lines.append(row(k, uptime(CFG["birthdate"]) if v == "{uptime}" and CFG.get("birthdate") else v))
    return lines


def svg(theme, lines):
    c = THEMES[theme]
    art_w = max(len(l) for l in ASCII) * FONT * 0.6 + 70
    data_x = int(art_w)
    w = int(data_x + WIDTH * FONT * 0.62 + 30)
    h = max(len(ASCII), len(lines)) * LINE_H + 50
    art_y0 = 30 + (h - 50 - len(ASCII) * LINE_H) // 2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" font-family="Consolas,Menlo,\'DejaVu Sans Mono\',\'Courier New\',monospace" xml:space="preserve" '
           f'width="{w}px" height="{h}px" font-size="{FONT}px">',
           "<style>"
           f".key{{fill:{c['key']}}}.text{{fill:{c['text']}}}.dots{{fill:{c['dots']}}}"
           f".add{{fill:{c['add']}}}.del{{fill:{c['del']}}}"
           "text,tspan{white-space:pre}</style>",
           f'<rect width="{w}px" height="{h}px" fill="{c["bg"]}" rx="15"/>',
           f'<text x="20" y="{art_y0}" fill="{c["art"]}">']
    for i, l in enumerate(ASCII):
        out.append(f'<tspan x="20" y="{art_y0 + i * LINE_H}">{escape(l)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="{data_x}" y="30" fill="{c["text"]}">')
    for i, parts in enumerate(lines):
        spans = "".join(f'<tspan class="{cls}">{escape(t)}</tspan>' for cls, t in parts)
        out.append(f'<tspan x="{data_x}" y="{30 + i * LINE_H}">{spans}</tspan>')
    out.append("</text></svg>")
    return "\n".join(out)


if __name__ == "__main__":
    lines = build_lines(github_stats(CFG["username"]))
    for t in THEMES:
        with open(os.path.join(ROOT, f"{t}_mode.svg"), "w", encoding="utf-8") as f:
            f.write(svg(t, lines))
    print("Listo: dark_mode.svg y light_mode.svg")
