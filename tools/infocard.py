"""Render the neofetch-style info card.

Static: regenerate by hand when the details change, not on the daily cron.

Usage: python tools/infocard.py
"""
from brand import (BLUE, BLUE_2, DARK, INK, LINE, MINT, MONO, MUTED,
                   card_open, esc, title, write)

ROWS = [
    ("name", "Gabriel Andrei Villanueva"),
    ("role", "Web Developer & Designer"),
    ("now", "Isla Outsourcing Solutions"),
    ("prev", "Monte Carlo Technologies"),
    ("school", "BS Computer Engineering, PLSP"),
    ("stack", "Laravel / React / Next.js / TS"),
    ("data", "MySQL / PostgreSQL / Supabase"),
    ("design", "UI/UX / Brand Identity / Figma"),
    ("roles", "6 since 2022"),
    ("site", "engrgab.dev"),
]


def info_card():
    PAD_X, TOP, STEP = 26, 78, 21
    W = 450
    H = TOP + len(ROWS) * STEP + 34

    out = [card_open(W, H, "Profile summary")]
    out.append(title(PAD_X, 40, "gabbygab@github"))

    for i, (key, value) in enumerate(ROWS):
        y = TOP + i * STEP
        out.append(
            '  <g class="fade" style="animation-delay:%.2fs">'
            '<text x="%d" y="%d" font-family="%s" font-size="11.5" font-weight="700" '
            'fill="%s">%s</text>'
            '<text x="%d" y="%d" font-size="12" fill="%s">%s</text></g>\n'
            % (0.07 * i, PAD_X, y, MONO, BLUE, esc(key),
               PAD_X + 74, y, DARK, esc(value))
        )

    # the palette strip neofetch prints at the bottom
    sw, y = 15, TOP + len(ROWS) * STEP + 8
    for i, color in enumerate([INK, DARK, MUTED, "#A9B6CF", LINE, MINT, BLUE_2, BLUE]):
        out.append(
            '  <rect x="%d" y="%d" width="%d" height="9" rx="2" fill="%s" />\n'
            % (PAD_X + i * (sw + 4), y, sw, color)
        )

    out.append("</svg>\n")
    return "".join(out)


if __name__ == "__main__":
    write("info-card.svg", info_card())
