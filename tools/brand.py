"""Shared palette, type and SVG helpers for the generated profile art.

Palette and font come from the portfolio itself (resources/sass/app.scss and
tailwind.config.js): paper white, ink black, amber #FFC107 leading, orange
#FF9016 supporting, Poppins throughout.

Poppins is embedded as base64 WOFF2 because GitHub strips external font
references from an SVG but keeps an inline @font-face.
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

AMBER = "#FFC107"
ORANGE = "#FF9016"
PAPER = "#FFFFFF"
INK = "#0B0B0C"
DARK = "#353535"
MUTED = "#5D5D5D"
LINE = "#E2E2E2"
TRACK = "#F1F1F1"

FONT = "'PoppinsEmb', Poppins, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace"

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
    return (
        str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def card_open(w, h, label, radius=14):
    """Opening tags for a paper card matching the README's heading pills."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
        'height="%d" role="img" aria-label="%s">\n'
        "  <style>\n%s\n    text { font-family: %s; }\n"
        "    .fade { opacity: 0; animation: in .6s ease-out forwards; }\n"
        "    @keyframes in { to { opacity: 1 } }\n  </style>\n"
        '  <rect width="%d" height="%d" rx="%d" fill="%s" />\n'
        '  <rect x="0.6" y="0.6" width="%.1f" height="%.1f" rx="%d" fill="none" '
        'stroke="%s" stroke-width="1.2" />\n'
        % (w, h, w, h, esc(label), FACE, FONT, w, h, radius, PAPER,
           w - 1.2, h - 1.2, radius, LINE)
    )


def title(x, y, text, size=17, rule=46):
    """Card title plus the short amber rule used under every heading."""
    out = (
        '  <text x="%d" y="%d" font-size="%d" font-weight="700" fill="%s">%s</text>\n'
        % (x, y, size, INK, esc(text))
    )
    if rule:
        out += '  <rect x="%d" y="%d" width="%d" height="3" rx="1.5" fill="%s" />\n' % (
            x, y + 12, rule, AMBER,
        )
    return out


def write(name, body):
    path = os.path.join(ASSETS, name)
    io.open(path, "w", encoding="utf-8").write(body)
    print("wrote %s (%d bytes)" % (name, len(body.encode("utf-8"))))
