#!/usr/bin/env python3
"""
Genera un SVG de Top Languages a partir de las estadísticas reales de GitHub.
Uso: python generate_langs.py
Requiere: GITHUB_TOKEN como variable de entorno (o en el workflow)
"""

import os
import json
import urllib.request
import urllib.error
from collections import defaultdict

#  CONFIGURACIÓN
GITHUB_USER   = os.environ.get("GITHUB_USER", "TU_USUARIO")
MAX_LANGS     = 6
EXCLUDE_LANGS = {"HTML", "CSS", "Dockerfile", "Shell", "Makefile", "TeX"}  # ignorar estos

# Paleta colores
NEON_COLORS = [
    "#00F5FF",   # cyan
    "#FF00FF",   # magenta
    "#39FF14",   # verde eléctrico
    "#FF6B35",   # naranja neon
    "#BF00FF",   # violeta neon
    "#FFFF00",   # amarillo neon
]

#  FETCH DE DATOS VÍA GITHUB API

def fetch(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "top-langs-badge")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_language_stats(user, token):
    lang_bytes = defaultdict(int)
    page = 1

    while True:
        url = (f"https://api.github.com/users/{user}/repos"
               f"?per_page=100&page={page}&type=owner")
        repos = fetch(url, token)
        if not repos:
            break

        for repo in repos:
            if repo.get("fork"):
                continue
            langs_url = repo["languages_url"]
            try:
                langs = fetch(langs_url, token)
                for lang, count in langs.items():
                    if lang not in EXCLUDE_LANGS:
                        lang_bytes[lang] += count
            except Exception:
                pass

        page += 1
        if len(repos) < 100:
            break

    return lang_bytes

#  GENERACIÓN DEL SVG

def generate_svg(lang_stats):
    # ordenar y tomar top N
    sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)[:MAX_LANGS]
    total = sum(b for _, b in sorted_langs)
    if total == 0:
        print("No se encontraron datos de lenguajes.")
        return

    langs = [{"name": n, "pct": round(b / total * 100, 1), "color": NEON_COLORS[i % len(NEON_COLORS)]}
             for i, (n, b) in enumerate(sorted_langs)]

    # dimensiones
    W = 340
    PADDING = 24
    TITLE_H = 40
    ROW_H = 34
    BAR_H = 8
    H = TITLE_H + len(langs) * ROW_H + PADDING

    rows = []
    for i, l in enumerate(langs):
        y = TITLE_H + i * ROW_H
        bar_w = max(4, round((l["pct"] / 100) * (W - PADDING * 2)))
        glow_id = f"glow{i}"
        rows.append(f"""
    <!-- {l['name']} -->
    <defs>
      <filter id="{glow_id}" x="-20%" y="-80%" width="140%" height="260%">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>
    <text x="{PADDING}" y="{y + 13}" fill="#E0E0E0" font-family="'Courier New', monospace"
          font-size="12" font-weight="600">{l['name']}</text>
    <text x="{W - PADDING}" y="{y + 13}" fill="{l['color']}" font-family="'Courier New', monospace"
          font-size="11" text-anchor="end" font-weight="700">{l['pct']}%</text>
    <!-- track -->
    <rect x="{PADDING}" y="{y + 19}" width="{W - PADDING * 2}" height="{BAR_H}"
          rx="4" fill="#1E1E2E"/>
    <!-- barra activa -->
    <rect x="{PADDING}" y="{y + 19}" width="{bar_w}" height="{BAR_H}"
          rx="4" fill="{l['color']}" filter="url(#{glow_id})" opacity="0.9">
      <animate attributeName="width" from="0" to="{bar_w}" dur="0.8s"
               begin="{i * 0.12}s" fill="freeze" calcMode="spline"
               keySplines="0.4 0 0.2 1" keyTimes="0 1"/>
    </rect>""")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img" aria-label="Top Languages">

  <defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%"   stop-color="#0D0D1A"/>
      <stop offset="100%" stop-color="#12121F"/>
    </linearGradient>
    <filter id="titleGlow" x="-10%" y="-50%" width="120%" height="200%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- fondo -->
  <rect width="{W}" height="{H}" rx="12" fill="url(#bgGrad)" stroke="#2A2A3E" stroke-width="1.5"/>

  <!-- título -->
  <text x="{PADDING}" y="28" fill="#00F5FF" font-family="'Courier New', monospace"
        font-size="14" font-weight="700" filter="url(#titleGlow)">◈ Top Languages</text>
  <line x1="{PADDING}" y1="34" x2="{W - PADDING}" y2="34" stroke="#2A2A3E" stroke-width="1"/>

  {''.join(rows)}
</svg>"""

    out_path = os.path.join(os.path.dirname(__file__), "..", "assets", "top-langs.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"SVG generado en {out_path}")
    for l in langs:
        print(f"   {l['name']:20s} {l['pct']:5.1f}%  {l['color']}")

#  MAIN
if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN", "")
    user  = os.environ.get("GITHUB_USER", GITHUB_USER)

    if not token:
        raise SystemExit("Falta GITHUB_TOKEN como variable de entorno.")
    if user == "TU_USUARIO":
        raise SystemExit("Falta GITHUB_USER como variable de entorno.")

    print(f"Obteniendo stats de @{user}...")
    stats = get_language_stats(user, token)
    generate_svg(stats)
