"""Render the ASCII portrait and the neofetch-style info card.

Both are static: regenerate them by hand when the photo or the details change,
not on the daily cron.

The portrait converts assets/avatar.png to a character grid. The avatar is
already a circular cutout, so its alpha channel blanks everything outside the
circle to spaces -- no background removal needed. Rows are revealed by a
left-to-right clip wipe, staggered top to bottom, so the portrait types itself
in once and freezes.

Usage: python tools/portrait.py
"""
import os

from PIL import Image, ImageOps

from brand import (AMBER, ASSETS, DARK, FONT, INK, LINE, MONO, MUTED, ORANGE,
                   card_open, esc, title, write)

SRC = os.path.join(ASSETS, "avatar.png")

# bright (sparse) -> dark (dense); the leading space clears the background
RAMP = " .`:-=+*csS#%@"

COLS = 58
CHAR_W = 0.60   # monospace advance, in em
LINE_H = 1.00   # em per row


def to_rows(path, cols=COLS):
    """-> list of equal-length strings, one per character row."""
    im = Image.open(path).convert("RGBA")
    rows = int(round(cols * CHAR_W / LINE_H))

    small = im.resize((cols, rows), Image.LANCZOS)
    alpha = small.getchannel("A")
    grey = ImageOps.autocontrast(small.convert("L"), cutoff=3)

    out = []
    for y in range(rows):
        line = []
        for x in range(cols):
            if alpha.getpixel((x, y)) < 128:
                line.append(" ")
                continue
            # dark pixels take the dense end of the ramp
            idx = int((255 - grey.getpixel((x, y))) * (len(RAMP) - 1) / 255)
            line.append(RAMP[idx])
        out.append("".join(line))
    return out


def ascii_card(rows):
    FS = 10.0                     # font-size in user units
    cw, lh = FS * CHAR_W, FS * LINE_H
    PAD_X, TOP = 26, 74
    grid_w = len(rows[0]) * cw

    W = int(PAD_X * 2 + grid_w)
    H = int(TOP + len(rows) * lh + 26)

    out = [card_open(W, H, "ASCII portrait of Gabriel Andrei Villanueva")]
    out.append(title(PAD_X, 40, "whoami"))

    out.append("  <defs>\n")
    for i in range(len(rows)):
        out.append(
            '    <clipPath id="w%d"><rect x="%d" y="%.2f" width="0" height="%.2f">'
            '<animate attributeName="width" to="%.2f" dur=".45s" begin="%.2fs" '
            'fill="freeze" /></rect></clipPath>\n'
            % (i, PAD_X, TOP + i * lh - FS, lh + 2, grid_w, 0.055 * i)
        )
    out.append("  </defs>\n")

    for i, line in enumerate(rows):
        if not line.strip():
            continue
        out.append(
            '  <text clip-path="url(#w%d)" x="%d" y="%.2f" font-family="%s" '
            'font-size="%.2f" fill="%s" xml:space="preserve" textLength="%.2f" '
            'lengthAdjust="spacingAndGlyphs">%s</text>\n'
            % (i, PAD_X, TOP + i * lh, MONO, FS, DARK, grid_w, esc(line))
        )

    # cursor parks under the last row once the portrait has finished printing
    out.append(
        '  <rect x="%d" y="%.2f" width="%.2f" height="%.2f" fill="%s" opacity="0">'
        '<animate attributeName="opacity" values="0;1;1;0" dur="1.1s" begin="%.2fs" '
        'repeatCount="indefinite" /></rect>\n'
        % (PAD_X, TOP + len(rows) * lh - FS + 2, cw, FS, AMBER, 0.055 * len(rows))
    )

    out.append("</svg>\n")
    return "".join(out)


ROWS = [
    ("name", "Gabriel Andrei Villanueva"),
    ("role", "Full Stack Dev | Graphic & UI/UX"),
    ("now", "Isla Outsourcing Solutions"),
    ("prev", "Monte Carlo Technologies"),
    ("school", "BS Computer Engineering, PLSP"),
    ("stack", "Laravel / Vue / Angular / TS"),
    ("data", "MySQL / PostgreSQL / Supabase"),
    ("design", "Figma / Photoshop / Premiere"),
    ("roles", "6 since 2022"),
    ("site", "engrgab.gt.tc"),
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
            % (0.07 * i, PAD_X, y, MONO, ORANGE, esc(key),
               PAD_X + 74, y, DARK, esc(value))
        )

    # the palette strip neofetch prints at the bottom
    sw, y = 15, TOP + len(ROWS) * STEP + 8
    for i, color in enumerate([INK, DARK, MUTED, "#BFBFBF", LINE, AMBER, ORANGE]):
        out.append(
            '  <rect x="%d" y="%d" width="%d" height="9" rx="2" fill="%s" />\n'
            % (PAD_X + i * (sw + 4), y, sw, color)
        )

    out.append("</svg>\n")
    return "".join(out)


if __name__ == "__main__":
    grid = to_rows(SRC)
    print("ascii grid: %dx%d" % (len(grid[0]), len(grid)))
    write("ascii.svg", ascii_card(grid))
    write("info-card.svg", info_card())
