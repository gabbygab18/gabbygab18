"""Render the contribution calendar as a branded, animated SVG.

GitHub serves the calendar as public HTML at /users/<name>/contributions -- the
same fragment the profile page uses -- so this needs no token and no API quota.
Exact per-day counts live in the <tool-tip> text; the <td> carries only a
bucketed data-level, so the two are joined on the cell id.

Parsed with a regex rather than BeautifulSoup to keep the daily workflow free
of third-party dependencies.

Usage: python tools/heatmap.py [username]
"""
import re
import sys
import urllib.request

from brand import AMBER, DARK, INK, LINE, MUTED, card_open, esc, title, write

USER = sys.argv[1] if len(sys.argv) > 1 else "gabbygab18"

# none -> busiest, in the portfolio's amber
RAMP = ["#F1F1F1", "#FFE9A8", "#FFD257", "#FFC107", "#FF9016"]

CELL = re.compile(
    r'<td[^>]*?id="(contribution-day-component-\d+-\d+)"[^>]*?'
    r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d)"',
)
# the same attributes also appear in the other order
CELL_ALT = re.compile(
    r'<td[^>]*?data-date="(\d{4}-\d{2}-\d{2})"[^>]*?'
    r'id="(contribution-day-component-\d+-\d+)"[^>]*?data-level="(\d)"',
)
TIP = re.compile(r'<tool-tip[^>]*?for="(contribution-day-component-\d+-\d+)"[^>]*?>([^<]*)')
COUNT = re.compile(r"^(No|[\d,]+) contribution")


def fetch(user):
    req = urllib.request.Request(
        "https://github.com/users/%s/contributions" % user,
        headers={"User-Agent": "gabbygab18-profile-art"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse(html):
    """-> [(row, col, date, level, count)].

    The cell id is contribution-day-component-<weekday>-<week>, so the grid
    position comes straight out of the markup; the document itself is ordered
    one weekday row at a time, not week by week.
    """
    counts = {}
    for cell_id, text in TIP.findall(html):
        m = COUNT.match(text.strip())
        if m:
            raw = m.group(1)
            counts[cell_id] = 0 if raw == "No" else int(raw.replace(",", ""))

    found = CELL.findall(html)
    if not found:
        found = [(cid, date, lvl) for date, cid, lvl in CELL_ALT.findall(html)]
    if not found:
        raise SystemExit("no contribution cells found - GitHub markup changed?")

    days = []
    for cell_id, date, level in found:
        row, col = (int(n) for n in cell_id.rsplit("-", 2)[-2:])
        days.append((row, col, date, int(level), counts.get(cell_id, 0)))
    return days


def render(days):
    BOX, GAP = 11, 3
    PAD_X, TOP = 26, 74
    step = BOX + GAP

    cols = max(d[1] for d in days) + 1
    W = PAD_X * 2 + cols * step - GAP
    H = TOP + 7 * step + 46

    out = [card_open(W, H, "%s contribution calendar" % USER)]
    out.append(title(PAD_X, 40, "Contribution Graph"))

    for row, col, date, level, count in days:
        x = PAD_X + col * step
        y = TOP + row * step
        # Diagonal sweep: later columns and lower rows start later.
        delay = 0.012 * col + 0.05 * row
        label = "%d contribution%s on %s" % (count, "" if count == 1 else "s", date)
        out.append(
            '  <rect x="%d" y="%d" width="%d" height="%d" rx="2.5" fill="%s" '
            'opacity="0"><title>%s</title>'
            '<animate attributeName="opacity" to="1" dur=".35s" begin="%.2fs" '
            'fill="freeze" /></rect>\n'
            % (x, y, BOX, BOX, RAMP[level], esc(label), delay)
        )

    total = sum(d[4] for d in days)
    foot_y = TOP + 7 * step + 26
    out.append(
        '  <text x="%d" y="%d" font-size="12" fill="%s">'
        '<tspan font-weight="700" fill="%s">%s</tspan> contributions in the last year'
        "</text>\n" % (PAD_X, foot_y, DARK, INK, "{:,}".format(total))
    )

    # Less -> More legend, right aligned against the grid.
    lx = W - PAD_X - (len(RAMP) * step - GAP) - 76
    out.append(
        '  <text x="%d" y="%d" font-size="11" fill="%s">Less</text>\n'
        % (lx, foot_y, MUTED)
    )
    for i, color in enumerate(RAMP):
        out.append(
            '  <rect x="%d" y="%d" width="%d" height="%d" rx="2.5" fill="%s" />\n'
            % (lx + 34 + i * step, foot_y - 9, BOX, BOX, color)
        )
    out.append(
        '  <text x="%d" y="%d" font-size="11" fill="%s">More</text>\n'
        % (lx + 34 + len(RAMP) * step + 4, foot_y, MUTED)
    )

    out.append("</svg>\n")
    return "".join(out)


if __name__ == "__main__":
    parsed = parse(fetch(USER))
    print("%d days, %d contributions" % (len(parsed), sum(d[4] for d in parsed)))
    write("heatmap.svg", render(parsed))
