"""Render the GitHub stats and top-languages cards as branded SVGs.

github-readme-stats' public instance is permanently paused (503
DEPLOYMENT_PAUSED), and its themes cannot match this profile anyway: the rest
of the README uses Poppins on paper with the portfolio's amber. So the cards
are drawn here from the GitHub API, in that same design language, and a
scheduled workflow keeps them current.

The rank letter uses github-readme-stats' own published formula
(src/calculateRank.js) so the grade means the same thing it does there.

Usage: GITHUB_TOKEN=... python tools/cards.py [username]
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

USER = sys.argv[1] if len(sys.argv) > 1 else "gabbygab18"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# portfolio palette (resources/sass/app.scss + tailwind.config.js)
AMBER = "#FFC107"
ORANGE = "#FF9016"
PAPER = "#FFFFFF"
INK = "#0B0B0C"
DARK = "#353535"
MUTED = "#5D5D5D"
LINE = "#E2E2E2"
TRACK = "#F1F1F1"

# Languages GitHub has no strong colour for fall back to these, in order.
LANG_COLORS = {
    "JavaScript": "#F1E05A", "TypeScript": "#3178C6", "PHP": "#4F5D95",
    "HTML": "#E34C26", "CSS": "#563D7C", "SCSS": "#C6538C", "Less": "#1D365D",
    "Vue": "#41B883", "Blade": "#F7523F", "Python": "#3572A5", "Java": "#B07219",
    "C++": "#F34B7D", "C": "#555555", "C#": "#178600", "Shell": "#89E051",
    "Dart": "#00B4AB", "Ruby": "#701516", "Go": "#00ADD8", "TeX": "#3D6117",
    "Astro": "#FF5A03", "Svelte": "#FF3E00", "Jupyter Notebook": "#DA5B0B",
}
FALLBACK = ["#FFC107", "#FF9016", "#8A6A2F", "#BFBFBF", "#D9B45B", "#7A7A7A"]

FONT = "'PoppinsEmb', Poppins, 'Segoe UI', Helvetica, Arial, sans-serif"
FACE = (
    "    @font-face { font-family: 'PoppinsEmb'; font-weight: 400;\n"
    "      src: url(data:font/woff2;base64,%s) format('woff2'); }\n"
    "    @font-face { font-family: 'PoppinsEmb'; font-weight: 700;\n"
    "      src: url(data:font/woff2;base64,%s) format('woff2'); }"
) % (
    io.open(os.path.join(HERE, "poppins-400.b64")).read().strip(),
    io.open(os.path.join(HERE, "poppins-700.b64")).read().strip(),
)


def esc(text):
    """A bare & or < makes the whole SVG fail to parse."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def api(path, preview=None):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", preview or "application/vnd.github+json")
    req.add_header("User-Agent", "gabbygab18-profile-cards")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search_count(query, preview=None):
    """Search endpoints only need total_count, and they fail soft: a rate-limit
    or outage should leave a stale-but-sane card, not crash the workflow."""
    try:
        return api("/search/" + query + "&per_page=1", preview)["total_count"]
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as exc:
        print("warning: search '%s' failed (%s), counting 0" % (query, exc))
        return 0


# --------------------------------------------------------------------- rank
def exponential_cdf(x):
    return 1 - 2 ** -x


def log_normal_cdf(x):
    return x / (1 + x)


def calculate_rank(commits, prs, issues, reviews, stars, followers):
    """Port of github-readme-stats src/calculateRank.js (all_commits=False)."""
    weights = {
        "commits": (250.0, 2), "prs": (50.0, 3), "issues": (25.0, 1),
        "reviews": (2.0, 1), "stars": (50.0, 4), "followers": (10.0, 1),
    }
    total_weight = sum(w for _, w in weights.values())

    score = (
        weights["commits"][1] * exponential_cdf(commits / weights["commits"][0])
        + weights["prs"][1] * exponential_cdf(prs / weights["prs"][0])
        + weights["issues"][1] * exponential_cdf(issues / weights["issues"][0])
        + weights["reviews"][1] * exponential_cdf(reviews / weights["reviews"][0])
        + weights["stars"][1] * log_normal_cdf(stars / weights["stars"][0])
        + weights["followers"][1] * log_normal_cdf(followers / weights["followers"][0])
    )
    rank = 1 - score / total_weight

    thresholds = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    pct = rank * 100
    for t, level in zip(thresholds, levels):
        if pct <= t:
            return level, pct
    return levels[-1], pct


# -------------------------------------------------------------------- fetch
def collect():
    user = api("/users/" + USER)
    repos, page = [], 1
    while True:
        batch = api("/users/%s/repos?per_page=100&page=%d" % (USER, page))
        repos += batch
        if len(batch) < 100:
            break
        page += 1

    owned = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in owned)

    langs = {}
    for r in owned:
        if r.get("fork") or not r.get("language"):
            continue
        try:
            for name, size in api("/repos/%s/%s/languages" % (USER, r["name"])).items():
                langs[name] = langs.get(name, 0) + size
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            print("warning: languages for %s failed (%s)" % (r["name"], exc))

    commits = search_count(
        "commits?q=author:" + USER, "application/vnd.github.cloak-preview+json"
    )
    prs = search_count("issues?q=author:%s+type:pr" % USER)
    issues = search_count("issues?q=author:%s+type:issue" % USER)
    reviews = search_count("issues?q=reviewed-by:%s+type:pr" % USER)
    contributed = search_count("issues?q=author:%s+type:pr+is:merged" % USER)

    return {
        "stars": stars, "commits": commits, "prs": prs, "issues": issues,
        "reviews": reviews, "contributed": contributed,
        "followers": user["followers"], "repos": len(owned), "langs": langs,
    }


# ------------------------------------------------------------------- render
def card_open(w, h, label):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
        'height="%d" role="img" aria-label="%s">\n'
        "  <style>\n%s\n    text { font-family: %s; }\n"
        "    .fade { opacity: 0; animation: in .6s ease-out forwards; }\n"
        "    @keyframes in { to { opacity: 1 } }\n  </style>\n"
        '  <rect width="%d" height="%d" rx="14" fill="%s" />\n'
        '  <rect x="0.6" y="0.6" width="%.1f" height="%.1f" rx="14" fill="none" '
        'stroke="%s" stroke-width="1.2" />\n'
        % (w, h, w, h, esc(label), FACE, FONT, w, h, PAPER, w - 1.2, h - 1.2, LINE)
    )


def stats_card(d):
    W, H = 520, 210
    level, pct = calculate_rank(
        d["commits"], d["prs"], d["issues"], d["reviews"], d["stars"], d["followers"]
    )
    rows = [
        ("Total Stars Earned", d["stars"]),
        ("Total Commits", d["commits"]),
        ("Total PRs", d["prs"]),
        ("Total Issues", d["issues"]),
        ("Merged PRs", d["contributed"]),
    ]

    out = [card_open(W, H, "%s's GitHub stats" % USER)]
    out.append(
        '  <text x="26" y="40" font-size="17" font-weight="700" fill="%s">'
        "GitHub Stats</text>\n" % INK
    )
    out.append('  <rect x="26" y="52" width="46" height="3" rx="1.5" fill="%s" />\n' % AMBER)

    for i, (label, value) in enumerate(rows):
        y = 82 + i * 24
        out.append(
            '  <g class="fade" style="animation-delay:%.2fs">'
            '<text x="26" y="%d" font-size="13" fill="%s">%s</text>'
            '<text x="300" y="%d" font-size="13" font-weight="700" text-anchor="end" '
            'fill="%s">%s</text></g>\n'
            % (0.1 * i, y, DARK, esc(label), y, INK, value)
        )

    # Rank ring. The arc length is the percentile, so a better rank draws more.
    cx, cy, r = 420, 108, 52
    circ = 2 * 3.141592653589793 * r
    filled = circ * max(0.0, min(1.0, (100 - pct) / 100.0))
    out.append(
        '  <circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="8" />\n'
        '  <circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="8" '
        'stroke-linecap="round" stroke-dasharray="%.2f %.2f" '
        'transform="rotate(-90 %d %d)">\n'
        '    <animate attributeName="stroke-dasharray" from="0 %.2f" to="%.2f %.2f" '
        'dur="1.2s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" />\n'
        "  </circle>\n"
        % (cx, cy, r, TRACK, cx, cy, r, AMBER, filled, circ - filled, cx, cy,
           circ, filled, circ - filled)
    )
    # Letter only. The percentile reads backwards to most people -- a C is the
    # 95th percentile, which looks like praise -- so the grade speaks for itself.
    out.append(
        '  <text x="%d" y="%d" font-size="34" font-weight="700" text-anchor="middle" '
        'fill="%s">%s</text>\n' % (cx, cy + 12, INK, esc(level))
    )
    out.append("</svg>\n")
    return "".join(out)


def langs_card(d):
    W = 420
    langs = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:6]
    total = sum(v for _, v in langs) or 1
    rows = (len(langs) + 1) // 2
    H = 96 + rows * 24

    out = [card_open(W, H, "Most used languages")]
    out.append(
        '  <text x="26" y="40" font-size="17" font-weight="700" fill="%s">'
        "Most Used Languages</text>\n" % INK
    )
    out.append('  <rect x="26" y="52" width="46" height="3" rx="1.5" fill="%s" />\n' % AMBER)

    bar_x, bar_w, bar_y = 26, W - 52, 66
    out.append(
        '  <rect x="%d" y="%d" width="%d" height="10" rx="5" fill="%s" />\n'
        % (bar_x, bar_y, bar_w, TRACK)
    )
    out.append('  <g clip-path="url(#bar)">\n')
    out.append(
        '    <clipPath id="bar"><rect x="%d" y="%d" width="%d" height="10" rx="5" />'
        "</clipPath>\n" % (bar_x, bar_y, bar_w, )
    )

    x = float(bar_x)
    for i, (name, size) in enumerate(langs):
        w = bar_w * size / total
        color = LANG_COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        out.append(
            '    <rect x="%.2f" y="%d" width="0" height="10" fill="%s">'
            '<animate attributeName="width" to="%.2f" dur="1s" begin="%.2fs" '
            'fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" /></rect>\n'
            % (x, bar_y, color, w, 0.08 * i)
        )
        x += w
    out.append("  </g>\n")

    for i, (name, size) in enumerate(langs):
        col, row = i % 2, i // 2
        lx = 26 + col * (bar_w // 2 + 8)
        ly = 104 + row * 24
        color = LANG_COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        out.append(
            '  <g class="fade" style="animation-delay:%.2fs">'
            '<circle cx="%d" cy="%d" r="5" fill="%s" />'
            '<text x="%d" y="%d" font-size="12" fill="%s">%s %.2f%%</text></g>\n'
            % (0.08 * i, lx + 5, ly - 4, color, lx + 17, ly, DARK,
               esc(name), 100.0 * size / total)
        )

    out.append("</svg>\n")
    return "".join(out)


def main():
    data = collect()
    print(json.dumps({k: v for k, v in data.items() if k != "langs"}, indent=2))
    print("languages:", sorted(data["langs"], key=lambda k: -data["langs"][k])[:6])

    for name, body in (("card-stats.svg", stats_card(data)),
                       ("card-langs.svg", langs_card(data))):
        path = os.path.join(ASSETS, name)
        io.open(path, "w", encoding="utf-8").write(body)
        print("wrote %s (%d bytes)" % (name, len(body.encode("utf-8"))))


if __name__ == "__main__":
    main()
