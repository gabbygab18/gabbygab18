"""Subset Poppins (OFL) and write the base64 WOFF2 the card renderer embeds.

Run once by hand when the glyph set changes; the .b64 files are committed so
CI never needs network access or fontTools.
"""
import base64
import io
import os
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))

URLS = {
    400: "https://fonts.gstatic.com/s/poppins/v24/pxiEyp8kv8JHgFVrFJA.ttf",
    700: "https://fonts.gstatic.com/s/poppins/v24/pxiByp8kv8JHgFVrLCz7V1s.ttf",
}

GLYPHS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " .,:;!?'\"()[]{}/\\|&#@_-+=*%<>"
)


def build(weight, url):
    ttf = os.path.join(HERE, "poppins-%d.ttf" % weight)
    if not os.path.exists(ttf):
        urllib.request.urlretrieve(url, ttf)

    font = TTFont(ttf)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.desubroutinize = True
    opts.layout_features = ["kern", "liga"]
    opts.notdef_outline = False
    sub = subset.Subsetter(options=opts)
    sub.populate(text=GLYPHS)
    sub.subset(font)

    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    raw = buf.getvalue()

    io.open(os.path.join(HERE, "poppins-%d.b64" % weight), "w").write(
        base64.b64encode(raw).decode("ascii")
    )
    print("poppins-%d: %d bytes woff2" % (weight, len(raw)))


if __name__ == "__main__":
    for w, u in URLS.items():
        build(w, u)
