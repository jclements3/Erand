"""inkscape_frame.py — single source of truth for the Inkscape → authoring
frame offset used by the v2 neck pipeline.

Per HANDOFF.md, the v2 SVG (`erand47jc_v2.svg` and its optimized descendant
`erand47jc_v2_opt.svg`) is authored in an Inkscape coordinate frame whose
origin is shifted from the project-wide authoring frame by `(INKSCAPE_DX,
INKSCAPE_DY)`. To convert an Inkscape-frame coordinate to the authoring
frame, ADD `(INKSCAPE_DX, INKSCAPE_DY)`; to convert the other direction,
subtract them.

Before v2 this offset was (+51.9, +121.64). During the v2 viewBox update
the user shifted everything by +40.37 mm in Inkscape y, giving the current
value (+51.9, +81.27). Any downstream code that needs to cross between the
frames should import from here rather than redefining the constants.
"""

INKSCAPE_DX = 51.9
INKSCAPE_DY = 81.27    # post-viewBox-shift translation (v2 frame)


def to_authoring(pt):
    """Inkscape-frame (x, y) -> authoring-frame (x, y)."""
    return (pt[0] + INKSCAPE_DX, pt[1] + INKSCAPE_DY)


def to_inkscape(pt):
    """Authoring-frame (x, y) -> Inkscape-frame (x, y)."""
    return (pt[0] - INKSCAPE_DX, pt[1] - INKSCAPE_DY)
