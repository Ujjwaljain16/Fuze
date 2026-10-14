"""Render the PWA's square PNG icons from the lightning-bolt path in frontend/public/logo1.svg.

Android Chrome needs real PNG icons (192 and 512, and a maskable one) before it will install the app as a WebAPK,
which is what lets the PWA appear in the phone's share sheet; iOS needs a PNG apple-touch-icon. logo1.svg is a wide
wordmark, which makes a poor square icon, so this draws just the bolt on the app's dark background.

    python scripts/make_pwa_icons.py        # rewrites frontend/public/icons/*.png

Needs Pillow. The output is deterministic, so the PNGs can be committed and regenerated at will.
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
BACKGROUND = (15, 15, 30)                       # #0F0F1E, the manifest's background_color
GRADIENT = [(0.0, (77, 208, 225)), (0.5, (20, 184, 166)), (1.0, (16, 185, 129))]   # #4DD0E1 > #14B8A6 > #10B981

# "M13 2L3 14h9l-1 8 10-12h-9l1-8z" in logo1.svg's 24 x 24 icon space, as absolute points
BOLT = [(13, 2), (3, 14), (12, 14), (11, 22), (21, 10), (12, 10), (13, 2)]
BOLT_MIN, BOLT_MAX = (3, 2), (21, 22)           # its bounding box
SUPERSAMPLE = 4                                  # draw large, shrink: smooth edges without a vector library


def _gradient_at(t: float):
    for (t0, c0), (t1, c1) in zip(GRADIENT, GRADIENT[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return GRADIENT[-1][1]


def render(size: int, bolt_share: float, background=BACKGROUND, rounded: float = 0.0) -> Image.Image:
    """A size x size icon with the bolt filling `bolt_share` of the width/height (the rest is padding)."""
    big = size * SUPERSAMPLE
    scale = big * bolt_share / (BOLT_MAX[1] - BOLT_MIN[1])           # the bolt is taller than it is wide
    width, height = (BOLT_MAX[0] - BOLT_MIN[0]) * scale, (BOLT_MAX[1] - BOLT_MIN[1]) * scale
    left, top = (big - width) / 2, (big - height) / 2
    points = [(left + (x - BOLT_MIN[0]) * scale, top + (y - BOLT_MIN[1]) * scale) for x, y in BOLT]

    mask = Image.new("L", (big, big), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(points, fill=255)
    draw.line(points, fill=255, width=max(1, round(big * 0.012)), joint="curve")   # the rounded stroke of the SVG

    fill = Image.new("RGB", (big, big))
    pixels = fill.load()
    for y in range(big):                                              # a diagonal gradient, as in the logo
        for x in range(big):
            pixels[x, y] = _gradient_at((x + y) / (2 * (big - 1)))

    canvas = Image.new("RGBA", (big, big), background + (255,) if background else (0, 0, 0, 0))
    canvas.paste(fill, (0, 0), mask)
    if rounded:                                                       # transparent rounded corners ("any" icons)
        corner = Image.new("L", (big, big), 0)
        ImageDraw.Draw(corner).rounded_rectangle((0, 0, big - 1, big - 1), radius=round(big * rounded), fill=255)
        canvas.putalpha(corner)
    return canvas.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icons = {
        "icon-192.png": render(192, 0.62, rounded=0.22),
        "icon-512.png": render(512, 0.62, rounded=0.22),
        # maskable: full-bleed background and the bolt inside the central safe zone (a 40% radius circle)
        "maskable-512.png": render(512, 0.46),
        # iOS draws its own rounded corners and wants an opaque square
        "apple-touch-icon.png": render(180, 0.58),
    }
    for name, image in icons.items():
        image.save(OUT / name, optimize=True)
        print(f"wrote {OUT / name} ({image.size[0]}x{image.size[1]})")


if __name__ == "__main__":
    main()
