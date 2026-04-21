"""
make_jc_svg.py — emit a minimal erand47jc.svg containing only:
  - buffer circles (R=12 black outlines) and their note labels
  - pink polyline neck outline (produced by neck_geodesic.py)
  - brown PROBLEMv2 Bezier curve (produced by build_harp.py)

Run build_harp.py + neck_geodesic.py first to regenerate erand47.svg,
then this script filters to erand47jc.svg.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "erand47.svg")
DST = os.path.join(HERE, "erand47jc.svg")

with open(SRC) as fh:
    content = fh.read()

svg_open = re.search(r'<svg[^>]+>', content).group(0)
vb_match = re.search(r'viewBox="([^"]+)"', svg_open)
vb = vb_match.group(1).split()
vb_x, vb_y, vb_w, vb_h = (float(v) for v in vb)

# Buffer circles: r="12.0" black outline, no fill.
buffer_circles = re.findall(
    r'<circle cx="[^"]+" cy="[^"]+" r="12\.0" fill="none" stroke="#000"[^/]*/>',
    content,
)

# Buffer note labels: small text at font-size="5", inside each buffer circle.
buffer_labels = re.findall(
    r'<text x="[^"]+" y="[^"]+" text-anchor="middle" font-family="sans-serif" '
    r'font-size="5" fill="#000">[^<]+</text>',
    content,
)

# Pink polyline neck outline (from neck_geodesic.py).
pink_paths = re.findall(
    r'<path d="[^"]+"[^/]*stroke="#ff69b4"[^/]*/>',
    content,
)

# Brown PROBLEMv2 Bezier curve (from build_harp.py).
brown_paths = re.findall(
    r'<path d="[^"]+"[^/]*stroke="#8B4513"[^/]*/>',
    content,
)

parts = [
    svg_open,
    f'<rect x="{vb_x:.3f}" y="{vb_y:.3f}" width="{vb_w:.3f}" '
    f'height="{vb_h:.3f}" fill="#fff"/>',
]
parts.extend(buffer_circles)
parts.extend(buffer_labels)
parts.extend(pink_paths)
parts.extend(brown_paths)
parts.append("</svg>")

with open(DST, "w") as fh:
    fh.write("\n".join(parts))

print(
    f"Wrote {DST}: {len(buffer_circles)} buffer circles, "
    f"{len(buffer_labels)} labels, {len(pink_paths)} pink paths, "
    f"{len(brown_paths)} brown paths."
)
