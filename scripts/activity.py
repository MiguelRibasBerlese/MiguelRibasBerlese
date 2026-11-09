"""Gera assets/activity.svg: o gráfico de contribuições do GitHub no tema do README."""
import json, os, sys, urllib.request
from datetime import date

LOGIN = os.environ.get("GH_LOGIN", "MiguelRibasBerlese")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT", "assets/activity.svg")

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""

LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
COLORS = ["#161B22", "#0E3B33", "#11806C", "#22B89C", "#5EEAD4"]
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()


def fetch():
    if os.environ.get("FAKE"):
        import random
        from datetime import timedelta
        random.seed(3)
        start = date(2025, 11, 9)
        weeks = [{"contributionDays": [{"date": (start + timedelta(days=w * 7 + d)).isoformat(),
                                        "contributionCount": 0,
                                        "contributionLevel": random.choice(list(LEVEL))} for d in range(7)]}
                 for w in range(53)]
        return 512, weeks
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], cal["weeks"]


def render(total, weeks):
    cell, gap = 10, 2.5
    step = cell + gap
    x0, y0 = 30, 34
    W, H = 680, y0 + 7 * step + 34
    rects, css, labels = [], [], []
    last_month = None
    for wi, week in enumerate(weeks):
        x = x0 + wi * step
        css.append(f".w{wi}{{animation-delay:{0.15 + wi * 0.025:.3f}s}}")
        for day in week["contributionDays"]:
            d = date.fromisoformat(day["date"])
            lvl = LEVEL.get(day["contributionLevel"], 0)
            y = y0 + d.isoweekday() % 7 * step
            title = f'{day["contributionCount"]} contributions on {d.isoformat()}'
            rects.append(f'<rect class="c w{wi}" x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="2" '
                         f'fill="{COLORS[lvl]}"><title>{title}</title></rect>')
            if d.day <= 7 and d.month != last_month and d.isoweekday() % 7 == 0 and x < W - 30:
                labels.append(f'<text x="{x:.1f}" y="{y0 - 10}" class="m">{MONTHS[d.month - 1]}</text>')
                last_month = d.month
    for i, name in ((1, "mon"), (3, "wed"), (5, "fri")):
        labels.append(f'<text x="0" y="{y0 + i * step + 8.5:.1f}" class="m">{name}</text>')
    legend_x = W - 128
    legend = "".join(f'<rect x="{legend_x + 30 + i * step:.1f}" y="{H - 18}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>'
                     for i, c in enumerate(COLORS))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions in the last year">
<style>
.m{{font-family:ui-monospace,'SFMono-Regular',Consolas,Menlo,monospace;font-size:11px;fill:#8B949E}}
.t{{font-family:ui-monospace,'SFMono-Regular',Consolas,Menlo,monospace;font-size:12px;fill:#C9D1D9}}
.c{{opacity:0;animation:in .5s cubic-bezier(.22,1,.36,1) forwards}}
@keyframes in{{from{{opacity:0;transform:translateY(-3px)}}to{{opacity:1;transform:none}}}}
{chr(10).join(css)}
@media (prefers-reduced-motion: reduce){{.c{{animation:none;opacity:1}}}}
</style>
{chr(10).join(labels)}
{chr(10).join(rects)}
<text x="{x0}" y="{H - 9}" class="t">{total} contributions in the last year</text>
<text x="{legend_x}" y="{H - 9}" class="m">less</text>{legend}
<text x="{legend_x + 30 + 5 * step + 4:.1f}" y="{H - 9}" class="m">more</text>
</svg>'''


if __name__ == "__main__":
    total, weeks = fetch()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(total, weeks))
    print(f"wrote {OUT}: {total} contributions, {len(weeks)} weeks")
