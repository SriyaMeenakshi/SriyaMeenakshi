#!/usr/bin/env python3
"""Grow a cherry blossom (sakura) tree from your GitHub activity, drawn as an animated SVG.

- Size / branching  <- contributions in the last year
- Flower centres    <- the languages in your own repositories
- Fairy lights      <- your current daily streak
- Shape             <- reshuffled every day (seeded by the date)

Pure standard library. Run locally with no token to get demo data:
    python scripts/grow_plant.py
In GitHub Actions the built-in GITHUB_TOKEN is used.
"""
import datetime
import json
import math
import os
import random
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "SriyaMeenakshi")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("PLANT_OUT", "assets/plant.svg")

W, H = 900, 440
BASE_X, BASE_Y = 450, 352  # where the trunk touches the hill

FALLBACK_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "C++": "#f34b7d", "C": "#9aa0a6", "Java": "#b07219", "HTML": "#e34c26",
    "CSS": "#8a5cf6", "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051",
}
PINKS = ["#ffb7d5", "#ffc9de", "#ff9ec4", "#ffd9e8"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(first: 60, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
        edges { size node { name color } } } }
    }
  }
}
"""


# ----------------------------------------------------------------- data ----
def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "sakura-tree"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        user = json.load(r)["data"]["user"]

    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    today = datetime.date.today().isoformat()
    counts = [d["contributionCount"] for d in days if d["date"] <= today]

    streak = 0
    for i, c in enumerate(reversed(counts)):
        if c > 0:
            streak += 1
        elif i == 0:  # today not committed yet - don't break the streak
            continue
        else:
            break

    langs = {}
    for repo in user["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            color = e["node"]["color"] or FALLBACK_COLORS.get(name, "#ffe27a")
            size, _ = langs.get(name, (0, color))
            langs[name] = (size + e["size"], color)
    return {"total": cal["totalContributions"], "streak": streak, "langs": langs}


def demo():
    return {
        "total": 412, "streak": 9,
        "langs": {n: (s, FALLBACK_COLORS[n]) for n, s in
                  [("Python", 50), ("TypeScript", 28), ("JavaScript", 20),
                   ("C++", 14), ("Java", 9), ("C", 5)]},
    }


# ---------------------------------------------------------------- helpers --
def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    c1, c2 = c1.lstrip("#"), c2.lstrip("#")
    a = [int(c1[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


def stage(total):
    for limit, name in [(5, "seed"), (30, "sprout"), (120, "sapling"),
                        (400, "budding"), (900, "full bloom")]:
        if total < limit:
            return name
    return "ancient sakura"


def flower_def(fid, color):
    petals = "".join(
        f'<ellipse cy="-4.6" rx="3.7" ry="5" transform="rotate({r})"/>' for r in (0, 72, 144, 216, 288))
    return f'<g id="{fid}" fill="{color}">{petals}</g>'


# ----------------------------------------------------------------- draw ----
def build(data):
    today = datetime.date.today()
    rng = random.Random(today.isoformat())  # new shape every day
    total, streak = data["total"], data["streak"]

    growth = min(1.0, math.log1p(total) / math.log1p(1000))
    height = 50 + 205 * growth
    depth = 2 + int(round(4 * growth))
    trunk = height * 0.30

    langs = sorted(data["langs"].items(), key=lambda kv: -kv[1][0])[:6] or \
        [("Code", (1, "#ffe27a"))]
    lang_names = [n for n, _ in langs]
    lang_colors = [v[1] for _, v in langs]
    lang_weights = [v[0] for _, v in langs]

    segs, tips = [], []
    lean = rng.choice([-1, 1]) * rng.uniform(0.10, 0.2)  # sakura love a gentle lean

    def grow(x, y, ang, length, d, width):
        ang2 = ang + (lean * 0.25 if d == depth else 0)
        x2 = x + length * math.sin(ang2)
        y2 = y - length * math.cos(ang2)
        segs.append((x, y, x2, y2, width, d))
        if d == 0:
            tips.append((x2, y2, ang2))
            return
        n = 3 if (d < depth - 1 and rng.random() < 0.2) else 2
        spread = rng.uniform(0.38, 0.7)
        for i in range(n):
            a = ang2 + (i - (n - 1) / 2) * spread + rng.uniform(-0.15, 0.15)
            if d == depth:
                a = ang2 + lean + (i - 0.5) * spread * 1.2
            grow(x2, y2, a, length * rng.uniform(0.72, 0.84), d - 1, width * 0.7)

    w0 = 4 + 10 * growth
    grow(BASE_X, BASE_Y, 0, trunk, depth, w0)

    xs = [q for s in segs for q in (s[0], s[2])]
    ys = [q for s in segs for q in (s[1], s[3])]
    minx, maxx, miny = min(xs) - 22, max(xs) + 22, min(ys) - 22

    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
      f'font-family="ui-rounded,Nunito,Segoe UI,sans-serif">')
    a(f"""<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1242"/>
<stop offset=".55" stop-color="#6b3f8f"/><stop offset="1" stop-color="#ffb3c7"/></linearGradient>
<radialGradient id="moon" cx="40%" cy="40%" r="70%"><stop offset="0" stop-color="#fffbe8"/>
<stop offset="1" stop-color="#ffe7a8"/></radialGradient>
<radialGradient id="halo"><stop offset="0" stop-color="#fff2c4" stop-opacity=".55"/>
<stop offset="1" stop-color="#fff2c4" stop-opacity="0"/></radialGradient>
<linearGradient id="hill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c58fd6"/>
<stop offset="1" stop-color="#4a2a78"/></linearGradient>
<filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="3" result="b"/>
<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
{flower_def("p1", "#ffb7d5")}
{flower_def("p2", "#ffd3e4")}
{flower_def("p3", "#ff9ec4")}
<path id="petal" d="M0,0 C4,-3 8,-1 7,3 C5,6 1,5 0,0Z"/>
<style>
.sway{{transform-origin:{BASE_X}px {BASE_Y}px;animation:sway 6s ease-in-out infinite alternate}}
@keyframes sway{{from{{transform:rotate(-1.2deg)}}to{{transform:rotate(1.2deg)}}}}
.tw{{animation:tw 3s ease-in-out infinite alternate}}
@keyframes tw{{from{{opacity:.2}}to{{opacity:1}}}}
.fall{{animation:fall linear infinite;opacity:0}}
@keyframes fall{{0%{{opacity:0;transform:translate(0,0) rotate(0)}}10%{{opacity:.95}}
90%{{opacity:.9}}100%{{opacity:0;transform:translate(var(--dx),{H}px) rotate(540deg)}}}}
.blink{{transform-box:fill-box;transform-origin:center;animation:blink 5s infinite}}
@keyframes blink{{0%,92%,100%{{transform:scaleY(1)}}95%{{transform:scaleY(.1)}}}}
.box{{fill:none;stroke-width:1.5;stroke-dasharray:6 4;opacity:.8}}
.lbl{{font-size:10px;font-weight:700}}
.hud{{font-size:11px;fill:#fff;opacity:.92}}
.float{{animation:float 5s ease-in-out infinite}}
@keyframes float{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(9px,-16px)}}}}
.wag{{transform-box:fill-box;transform-origin:0% 100%;animation:wag .7s ease-in-out infinite alternate}}
@keyframes wag{{from{{transform:rotate(-14deg)}}to{{transform:rotate(22deg)}}}}
.flame{{animation:flame 1.2s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:50% 100%}}
@keyframes flame{{from{{transform:scale(.8)}}to{{transform:scale(1.15)}}}}
</style></defs>""")
    a(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')

    for _ in range(80):
        sx, sy, r = rng.uniform(0, W), rng.uniform(0, H * 0.55), rng.choice([.6, .9, 1.2, 1.6])
        a(f'<circle class="tw" cx="{sx:.0f}" cy="{sy:.0f}" r="{r}" fill="#fff" '
          f'style="animation-delay:{rng.uniform(0, 3):.1f}s"/>')

    # big cute moon with halo + tiny orbiting satellite
    a('<circle cx="740" cy="105" r="95" fill="url(#halo)"/><circle cx="740" cy="105" r="46" fill="url(#moon)"/>'
      '<g fill="#f3d98b" opacity=".6"><circle cx="725" cy="95" r="7"/><circle cx="757" cy="119" r="5"/>'
      '<circle cx="752" cy="85" r="3.5"/></g>')
    a('<g><circle r="3" fill="#fff"/><circle r="6" fill="#fff" opacity=".25"/>'
      '<animateMotion dur="30s" repeatCount="indefinite" path="M 90,170 Q 450,-40 820,170"/></g>')

    # hill
    a(f'<ellipse cx="450" cy="{BASE_Y + 270}" rx="640" ry="300" fill="url(#hill)"/>')
    a(f'<ellipse cx="450" cy="{BASE_Y + 2}" rx="170" ry="9" fill="#ffd9ee" opacity=".25"/>')
    for _ in range(26):  # petals resting on the ground
        px = BASE_X + rng.gauss(0, 150)
        py = BASE_Y + rng.uniform(2, 38)
        a(f'<use href="#petal" transform="translate({px:.0f} {py:.0f}) rotate({rng.uniform(0, 360):.0f}) scale(.8)" '
          f'fill="{rng.choice(PINKS)}" opacity=".85"/>')

    # tree
    a('<g class="sway">')
    for x1, y1, x2, y2, w, d in segs:
        col = mix("#5b3a45", "#8a5a62", 1 - d / max(depth, 1))
        a(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" '
          f'stroke-width="{w:.1f}" stroke-linecap="round"/>')

    for x, y, ang in tips:  # soft blossom puffs
        a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(11, 17) * (0.6 + growth * .5):.1f}" '
          f'fill="{rng.choice(PINKS)}" opacity=".38"/>')

    def flower(x, y, size):
        ref = rng.choice(["p1", "p2", "p3", "p1", "p2"])
        rot = rng.uniform(0, 72)
        a(f'<use href="#{ref}" transform="translate({x:.1f} {y:.1f}) rotate({rot:.0f}) scale({size:.2f})"/>')
        c = rng.choices(lang_colors, weights=lang_weights)[0]
        a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.5 * size:.1f}" fill="{c}"/>')

    sc = 0.7 + growth * 0.5
    for x, y, ang in tips:
        for _ in range(3):
            flower(x + rng.uniform(-9, 9), y + rng.uniform(-9, 9), rng.uniform(.7, 1.15) * sc)
    for x1, y1, x2, y2, w, d in segs:
        if 0 < d <= 3 and rng.random() < 0.55:
            flower(x2 + rng.uniform(-4, 4), y2 + rng.uniform(-4, 4), rng.uniform(.6, 1) * sc)

    if growth > 0.22:  # kawaii face on the trunk
        fy = BASE_Y - trunk * 0.5
        s = 0.7 + w0 / 14
        a(f'<g transform="translate({BASE_X} {fy:.0f}) scale({s:.2f})">'
          '<circle class="blink" cx="-4" cy="0" r="1.7" fill="#2a1520"/>'
          '<circle class="blink" cx="4" cy="0" r="1.7" fill="#2a1520"/>'
          '<ellipse cx="-7.5" cy="3.5" rx="2.4" ry="1.4" fill="#ff8fb4" opacity=".85"/>'
          '<ellipse cx="7.5" cy="3.5" rx="2.4" ry="1.4" fill="#ff8fb4" opacity=".85"/>'
          '<path d="M-2,3 Q0,5.5 2,3" fill="none" stroke="#2a1520" stroke-width="1.1" stroke-linecap="round"/></g>')

    for i in range(min(streak, 14)):  # streak = glowing fairy lights
        x, y, _ = rng.choice(tips)
        x += rng.uniform(-12, 12)
        y += rng.uniform(-8, 14)
        a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#fff3a8" filter="url(#glow)">'
          f'<animate attributeName="opacity" values="1;.35;1" dur="{rng.uniform(1.6, 3.2):.1f}s" '
          f'repeatCount="indefinite"/></circle>')
    a("</g>")

    for _ in range(16):  # falling petals
        x = rng.uniform(minx - 10, maxx + 10)
        y = rng.uniform(miny, BASE_Y - trunk)
        dur = rng.uniform(7, 13)
        a(f'<g transform="translate({x:.0f} {y:.0f})"><use class="fall" href="#petal" '
          f'fill="{rng.choice(PINKS)}" style="--dx:{rng.uniform(-90, 90):.0f}px;'
          f'animation-duration:{dur:.1f}s;animation-delay:{-rng.uniform(0, dur):.1f}s"/></g>')

    # gentle "object detector" box
    conf = rng.uniform(0.95, 0.99)
    a(f'<rect class="box" x="{minx:.0f}" y="{miny:.0f}" width="{maxx-minx:.0f}" height="{BASE_Y+4-miny:.0f}" '
      f'rx="8" stroke="#ffd1e3"/>')
    txt = f"sakura {conf:.2f}"
    a(f'<rect x="{minx:.0f}" y="{miny-15:.0f}" width="{len(txt)*6.2+10:.0f}" height="15" rx="7" fill="#ffd1e3"/>')
    a(f'<text class="lbl" x="{minx+5:.0f}" y="{miny-4:.0f}" fill="#4a1d44">{escape(txt)}</text>')

    # golden retriever puppy sitting under the tree
    a(f'<g transform="translate({BASE_X + 118} {BASE_Y - 4}) scale(1.15)">'
      '<ellipse cx="0" cy="2" rx="17" ry="4" fill="#2a1450" opacity=".35"/>'
      '<path class="wag" d="M14,-6 Q28,-8 26,-24" fill="none" stroke="#e8b05a" stroke-width="6" stroke-linecap="round"/>'
      '<ellipse cx="0" cy="-12" rx="14" ry="13" fill="#e8b05a"/>'
      '<ellipse cx="-5" cy="-3" rx="4" ry="6" fill="#f0bf6e"/><ellipse cx="5" cy="-3" rx="4" ry="6" fill="#f0bf6e"/>'
      '<circle cx="0" cy="-30" r="13" fill="#f0bf6e"/>'
      '<ellipse cx="-12" cy="-29" rx="5" ry="9" transform="rotate(14 -12 -29)" fill="#c98a3a"/>'
      '<ellipse cx="12" cy="-29" rx="5" ry="9" transform="rotate(-14 12 -29)" fill="#c98a3a"/>'
      '<ellipse cx="0" cy="-25.5" rx="7" ry="5" fill="#f8dfae"/>'
      '<ellipse cx="0" cy="-28.5" rx="2.4" ry="1.8" fill="#2a1520"/>'
      '<ellipse cx="0" cy="-20" rx="2" ry="3" fill="#ff8fb4"/>'
      '<path d="M-3,-24 Q0,-21.5 3,-24" fill="none" stroke="#2a1520" stroke-width="1" stroke-linecap="round"/>'
      '<g class="blink"><circle cx="-5.5" cy="-33" r="1.9" fill="#2a1520"/><circle cx="5.5" cy="-33" r="1.9" fill="#2a1520"/>'
      '<circle cx="-4.9" cy="-33.7" r=".6" fill="#fff"/><circle cx="6.1" cy="-33.7" r=".6" fill="#fff"/></g>'
      '<ellipse cx="-9" cy="-27" rx="2.2" ry="1.3" fill="#ff8fb4" opacity=".7"/>'
      '<ellipse cx="9" cy="-27" rx="2.2" ry="1.3" fill="#ff8fb4" opacity=".7"/></g>')

    # flying lanterns: one with a puppy face, two tiny ones far away
    for lx_, ly_, sc_, op_, dl in [(80, 120, .4, .6, 1.2), (330, 70, .32, .5, 2.6)]:
        a(f'<g transform="translate({lx_} {ly_}) scale({sc_})" opacity="{op_}"><g class="float" style="animation-delay:{dl}s">'
          '<path d="M-20,-26 Q-26,0 -14,26 L14,26 Q26,0 20,-26 Z" fill="#ffcf70"/></g></g>')
    a('<g transform="translate(165 225)"><g class="float">'
      '<circle cx="0" cy="0" r="58" fill="url(#halo)"/>'
      '<ellipse cx="-19" cy="-22" rx="7" ry="13" transform="rotate(18 -19 -22)" fill="#c98a3a"/>'
      '<ellipse cx="19" cy="-22" rx="7" ry="13" transform="rotate(-18 19 -22)" fill="#c98a3a"/>'
      '<path d="M-22,-26 Q-30,0 -17,30 L17,30 Q30,0 22,-26 Z" fill="#ffd77c" filter="url(#glow)"/>'
      '<ellipse cx="0" cy="-26" rx="22" ry="5" fill="#f0bf6e"/>'
      '<ellipse cx="0" cy="8" rx="11" ry="8" fill="#fff0c4"/>'
      '<ellipse cx="0" cy="4" rx="3.2" ry="2.4" fill="#2a1520"/>'
      '<path d="M-4,9 Q0,13 4,9" fill="none" stroke="#2a1520" stroke-width="1.3" stroke-linecap="round"/>'
      '<ellipse cx="0" cy="14" rx="2.4" ry="3.2" fill="#ff8fb4"/>'
      '<g class="blink"><circle cx="-8" cy="-4" r="2.4" fill="#2a1520"/><circle cx="8" cy="-4" r="2.4" fill="#2a1520"/>'
      '<circle cx="-7.2" cy="-5" r=".8" fill="#fff"/><circle cx="8.8" cy="-5" r=".8" fill="#fff"/></g>'
      '<ellipse cx="-14" cy="5" rx="3.2" ry="2" fill="#ff8fb4" opacity=".75"/>'
      '<ellipse cx="14" cy="5" rx="3.2" ry="2" fill="#ff8fb4" opacity=".75"/>'
      '<path class="flame" d="M0,31 Q-4,38 0,45 Q4,38 0,31Z" fill="#ff9a3c" filter="url(#glow)"/>'
      '</g></g>')

    # HUD
    a('<text class="hud" x="18" y="26" font-weight="700" font-size="13">Prunus sriyae</text>')
    a(f'<text class="hud" x="18" y="46">stage · {stage(total)}</text>')
    a(f'<text class="hud" x="18" y="62">commits · {total} / 365d</text>')
    a(f'<text class="hud" x="18" y="78">streak · {streak} day{"s" if streak != 1 else ""}'
      f'{" ✨" if streak >= 3 else ""}</text>')
    a(f'<text class="hud" x="{W-18}" y="{H-12}" text-anchor="end">redrawn {today.isoformat()}</text>')

    lx = 18
    for name, col in zip(lang_names, lang_colors):
        a(f'<circle cx="{lx+4}" cy="{H-16}" r="4.5" fill="{col}"/>')
        a(f'<text class="hud" x="{lx+13}" y="{H-12}">{escape(name)}</text>')
        lx += 24 + len(name) * 6.8
    a("</svg>")
    return "\n".join(out)


def main():
    data = fetch() if TOKEN else demo()
    if not TOKEN:
        print("No GITHUB_TOKEN found - drawing demo data")
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(data))
    print(f"wrote {OUT}  commits={data['total']} streak={data['streak']}")


if __name__ == "__main__":
    main()
