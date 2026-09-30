"""Draw the app icon — a mala, the garland the book is named for — at every size.

One geometry, written out as the SVG favicon and rasterised (with Pillow,
supersampled for smooth edges) into the PNGs that iOS and the web app
manifest need. The icons are committed; run this only to change them:

    pip install pillow && python3 tools/build_icons.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

ICON_DIRECTORY = Path(__file__).parent.parent / "site" / "assets" / "icons"

PAPER = "#f7f2e8"
OCHRE = "#a35a26"
THREAD = "#c98a4e"

# In a 512-unit square. Few, large beads, so the ring still reads at 16px.
CENTRE_X, CENTRE_Y = 256, 238
RING_RADIUS = 150
BEAD_COUNT = 18
BEAD_RADIUS = 21
GURU_BEAD_RADIUS = 31
TASSEL = [(256, 402), (236, 470), (276, 470)]


def beads():
    """(x, y, radius) for every bead, the guru bead last, at the bottom."""
    result = []
    for index in range(BEAD_COUNT):
        angle = math.pi / 2 + 2 * math.pi * index / BEAD_COUNT
        if index == 0:
            continue  # the guru bead's place
        result.append((
            CENTRE_X + RING_RADIUS * math.cos(angle),
            CENTRE_Y + RING_RADIUS * math.sin(angle),
            BEAD_RADIUS,
        ))
    result.append((CENTRE_X, CENTRE_Y + RING_RADIUS, GURU_BEAD_RADIUS))
    return result


def svg(corner_radius):
    circles = "\n".join(
        f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{OCHRE}"/>' for x, y, r in beads()
    )
    tassel = " ".join(f"{x},{y}" for x, y in TASSEL)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="{corner_radius}" fill="{PAPER}"/>
  <circle cx="{CENTRE_X}" cy="{CENTRE_Y}" r="{RING_RADIUS}" fill="none" stroke="{THREAD}" stroke-width="6"/>
  <polygon points="{tassel}" fill="{OCHRE}"/>
{circles}
</svg>
"""


def png(size, scale=1.0, supersample=4):
    """Full-bleed square; iOS and the launcher round the corners themselves.

    scale < 1 shrinks the mala into the safe zone of a maskable icon.
    """
    canvas = size * supersample
    unit = canvas / 512
    image = Image.new("RGB", (canvas, canvas), PAPER)
    draw = ImageDraw.Draw(image)

    def at(x, y):
        return (canvas / 2 + (x - 256) * scale * unit, canvas / 2 + (y - 256) * scale * unit)

    ring = RING_RADIUS * scale * unit
    centre = at(CENTRE_X, CENTRE_Y)
    draw.ellipse(
        [centre[0] - ring, centre[1] - ring, centre[0] + ring, centre[1] + ring],
        outline=THREAD,
        width=max(1, round(6 * scale * unit)),
    )
    draw.polygon([at(x, y) for x, y in TASSEL], fill=OCHRE)
    for x, y, r in beads():
        cx, cy = at(x, y)
        radius = r * scale * unit
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=OCHRE)
    return image.resize((size, size), Image.LANCZOS)


def main():
    ICON_DIRECTORY.mkdir(parents=True, exist_ok=True)
    (ICON_DIRECTORY / "favicon.svg").write_text(svg(corner_radius=112))
    outputs = {
        "favicon-32.png": png(32),
        # A little margin, so the home-screen corner rounding clears the beads.
        "apple-touch-icon.png": png(180, scale=0.86),
        "icon-192.png": png(192, scale=0.86),
        "icon-512.png": png(512, scale=0.86),
        # Maskable icons may be cropped to a circle of 80% of the width.
        "icon-maskable-512.png": png(512, scale=0.78),
    }
    for name, image in outputs.items():
        image.save(ICON_DIRECTORY / name, optimize=True)
    print(f"{len(outputs) + 1} icons -> {ICON_DIRECTORY}")


if __name__ == "__main__":
    main()
