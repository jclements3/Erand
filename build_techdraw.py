"""Generate TechDraw orthographic SVGs from erand47.FCStd.

Produces engineering drawings with hidden-line removal (visible edges solid,
hidden edges dashed) using FreeCAD's TechDraw workbench. The hand-rolled
SVG pipeline (build_views.py) only emits silhouettes; this script captures
internal features such as plate slots, tongue-and-groove joints, and
internal bosses as proper dashed conventions.

Outputs:
    erand47_techdraw.svg          - Top / Front / Right of the full assembly
    erand47_shoulder_techdraw.svg - Shoulder-only detail at larger scale

Run headlessly:

    cat <<EOF | freecadcmd
    import sys; sys.path.insert(0, '/home/james.clements/projects/Erand')
    _p = '/home/james.clements/projects/Erand/build_techdraw.py'
    exec(open(_p).read(), {'__file__': _p, '__name__': '__main__'})
    EOF

How it actually works in FreeCAD 0.19 headless:

    `template.PageResult` only contains the unrendered template SVG when the
    GUI is absent, so we can't just read the page's composed SVG file. The
    workable path is `TechDraw.viewPartAsSvg(view)`, which returns a per-view
    SVG fragment (geometry only, in mm, centred at the view's local origin).
    FreeCAD encodes hidden-line classification via stroke-width: 0.7 mm =
    visible (HardVisible), 0.35 mm = hidden (HardHidden). It does NOT add
    `stroke-dasharray` itself, so we post-process the hidden group to use a
    proper dashed line style.

The script does NOT save the .FCStd source. Page/Template/View objects are
created in memory only and the document is closed without saving.
"""

import os
import re
import sys

import FreeCAD as App
import TechDraw


PROJECT_DIR = '/home/james.clements/projects/Erand'
SOURCE_FCSTD = os.path.join(PROJECT_DIR, 'erand47.FCStd')

OUT_FULL = os.path.join(PROJECT_DIR, 'erand47_techdraw.svg')
OUT_SHOULDER = os.path.join(PROJECT_DIR, 'erand47_shoulder_techdraw.svg')

# Top-level features the assembly drawing should depict. We don't hard-code a
# strict requirement: enumerate the doc, keep whichever of these names exist,
# and pick up any extra top-level Part::Feature added by other agents.
EXPECTED_NAMES = (
    'Chamber', 'BasePlug', 'Shoulder', 'Column',
    'NeckPlate_pz', 'NeckPlate_mz',
)

# FreeCAD encodes line-visibility classification by stroke-width.
VISIBLE_STROKE_WIDTHS = ('0.7', '0.70')
HIDDEN_STROKE_WIDTHS = ('0.35', '0.350')

# Layout padding between views (mm).
VIEW_GAP = 30.0
SVG_MARGIN = 20.0


def collect_assembly_sources(doc):
    """Return the list of top-level Part::Feature objects to project."""
    expected = [doc.getObject(n) for n in EXPECTED_NAMES]
    expected = [o for o in expected if o is not None]
    if expected:
        names = {o.Name for o in expected}
        for o in doc.Objects:
            if (
                o.Name not in names
                and o.TypeId.startswith('Part::')
                and hasattr(o, 'Shape')
                and o.Shape is not None
                and not o.Shape.isNull()
                and not o.InList  # top-level only
            ):
                expected.append(o)
                names.add(o.Name)
        return expected
    # Fallback: any top-level Part::Feature with a non-null shape.
    return [
        o for o in doc.Objects
        if o.TypeId.startswith('Part::')
        and hasattr(o, 'Shape')
        and o.Shape is not None
        and not o.Shape.isNull()
        and not o.InList
    ]


def configure_hlr(view):
    """Turn on hidden-line classification for a DrawProjGroupItem.

    HardHidden => emit hidden hard edges in the 0.35 mm group.
    SmoothHidden / SeamHidden / Iso* off so curved-surface noise stays out
    of the page.
    """
    view.HardHidden = True
    view.SmoothHidden = False
    view.SeamHidden = False
    view.IsoHidden = False
    view.IsoVisible = False
    view.IsoCount = 0


def build_proj_group(doc, page, name, sources):
    """Create a ProjGroup with Front/Top/Right views, HLR on. Return list of views."""
    pg = doc.addObject('TechDraw::DrawProjGroup', name)
    page.addView(pg)
    pg.Source = sources
    pg.ScaleType = 'Automatic'
    front = pg.addProjection('Front')
    top = pg.addProjection('Top')
    right = pg.addProjection('Right')
    views = [front, top, right]
    for v in views:
        configure_hlr(v)
    return pg, views


def style_hidden_group(svg_fragment):
    """Add stroke-dasharray to the 0.35-stroke group so hidden edges read as dashed.

    `viewPartAsSvg` emits two `<g>` containers: stroke-width="0.7" for visible
    edges and stroke-width="0.35" for hidden edges. We rewrite the hidden one
    to use a dashed style; the visible one keeps its default solid style.
    """
    def repl(m):
        opening = m.group(0)
        if 'stroke-dasharray' in opening:
            return opening
        # Insert before the closing '>'.
        return opening[:-1] + ' stroke-dasharray="2,1.5">'

    pattern = re.compile(r'<g\b[^>]*stroke-width="(?:0\.35|0\.350)"[^>]*>')
    return pattern.sub(repl, svg_fragment)


def view_bbox(svg_fragment):
    """Quick AABB over numeric tokens in the SVG fragment.

    The fragment consists of <path d="..."> tokens with absolute M/L/C/Q
    coordinates. We just scrape every signed float and infer alternating
    x/y. That's coarse but good enough for sizing the viewBox - we apply a
    generous margin around the union anyway.
    """
    nums = [float(s) for s in re.findall(r'-?\d+\.?\d*(?:[eE][-+]?\d+)?', svg_fragment)]
    if not nums:
        return (0.0, 0.0, 0.0, 0.0)
    # Filter outliers from stroke-width / opacity (small constants).
    # The geometry coordinates dominate; this is just for layout, so we don't
    # need to be precise.
    xs = nums[0::2]
    ys = nums[1::2]
    return (min(xs), min(ys), max(xs), max(ys))


def render_views_to_svg(views, dest_path, title):
    """Compose per-view SVG fragments into a single SVG file.

    Each view's fragment is in mm at scale=1 around the view's local centre.
    We translate by the view's (X, -Y) on the page, style hidden edges as
    dashed, and wrap the union in an SVG document.
    """
    fragments = []
    bboxes = []
    for v in views:
        raw = TechDraw.viewPartAsSvg(v)
        styled = style_hidden_group(raw)
        x = float(v.X)         # FreeCAD already uses mm
        y = float(v.Y)         # Y is up in FreeCAD, down in SVG
        # The fragment's coords are mm centred at the local origin AND already
        # multiplied by view.Scale (TechDraw bakes scale into the geometry).
        # We translate by the page position only.
        fragments.append((x, -y, styled))
        bb = view_bbox(styled)
        bboxes.append((x + bb[0], -y + bb[1], x + bb[2], -y + bb[3]))

    if not bboxes:
        raise RuntimeError(f'{title}: no views to render')

    minx = min(b[0] for b in bboxes) - SVG_MARGIN
    miny = min(b[1] for b in bboxes) - SVG_MARGIN
    maxx = max(b[2] for b in bboxes) + SVG_MARGIN
    maxy = max(b[3] for b in bboxes) + SVG_MARGIN
    width = maxx - minx
    height = maxy - miny

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1"',
        f'     width="{width:.2f}mm" height="{height:.2f}mm"',
        f'     viewBox="{minx:.2f} {miny:.2f} {width:.2f} {height:.2f}">',
        f'  <title>{title}</title>',
        '  <rect x="{:.2f}" y="{:.2f}" width="{:.2f}" height="{:.2f}" fill="#fff"/>'.format(
            minx, miny, width, height),
    ]

    for (tx, ty, frag), v in zip(fragments, views):
        label = v.Type if hasattr(v, 'Type') else v.Name
        parts.append(f'  <g id="view-{label}" transform="translate({tx:.4f},{ty:.4f})">')
        # Add a small label above the view (in mm).
        parts.append(
            f'    <text x="0" y="0" font-family="sans-serif" font-size="4"'
            f' fill="#444" text-anchor="middle">{label} (scale {v.Scale:.3f})</text>')
        parts.append(frag)
        parts.append('  </g>')

    parts.append('</svg>')

    out = '\n'.join(parts)
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(out)
    return len(out)


def main():
    if not os.path.exists(SOURCE_FCSTD):
        print(f'ERROR: missing source file {SOURCE_FCSTD}', file=sys.stderr)
        sys.exit(1)

    print(f'opening {SOURCE_FCSTD}')
    doc = App.openDocument(SOURCE_FCSTD)
    doc_name = doc.Name

    # Idempotency: remove any TechDraw scaffolding from a previous run.
    for name in ('PGFull', 'PageFull', 'TplFull',
                 'PGShoulder', 'PageShoulder', 'TplShoulder'):
        if doc.getObject(name) is not None:
            doc.removeObject(name)

    template_full = '/usr/share/freecad/Mod/TechDraw/Templates/A3_Landscape_blank.svg'
    template_detail = '/usr/share/freecad/Mod/TechDraw/Templates/A4_Landscape_blank.svg'

    # --- Full assembly page ---
    sources = collect_assembly_sources(doc)
    if not sources:
        print('ERROR: no Part::Feature sources found', file=sys.stderr)
        sys.exit(1)
    print(f'full-assembly sources: {[s.Name for s in sources]}')

    tpl_full = doc.addObject('TechDraw::DrawSVGTemplate', 'TplFull')
    tpl_full.Template = template_full
    page_full = doc.addObject('TechDraw::DrawPage', 'PageFull')
    page_full.Template = tpl_full
    pg_full, views_full = build_proj_group(doc, page_full, 'PGFull', sources)

    # --- Shoulder detail page ---
    shoulder = doc.getObject('Shoulder')
    pg_shoulder, views_shoulder = None, []
    if shoulder is not None:
        tpl_sh = doc.addObject('TechDraw::DrawSVGTemplate', 'TplShoulder')
        tpl_sh.Template = template_detail
        page_sh = doc.addObject('TechDraw::DrawPage', 'PageShoulder')
        page_sh.Template = tpl_sh
        pg_shoulder, views_shoulder = build_proj_group(
            doc, page_sh, 'PGShoulder', [shoulder])
    else:
        print('  (no Shoulder feature found; skipping detail page)')

    print('recomputing document (this is the slow HLR step)')
    doc.recompute()

    print('rendering full-assembly SVG')
    n_full = render_views_to_svg(views_full, OUT_FULL, 'Erand47 — assembly HLR')
    size_full = os.path.getsize(OUT_FULL)
    with open(OUT_FULL, 'r', encoding='utf-8') as f:
        has_dashed = 'stroke-dasharray' in f.read()
    print(f'  wrote {OUT_FULL} ({size_full:,} bytes, dashed={has_dashed})')

    if views_shoulder:
        print('rendering shoulder-detail SVG')
        render_views_to_svg(views_shoulder, OUT_SHOULDER, 'Erand47 — shoulder HLR detail')
        size_sh = os.path.getsize(OUT_SHOULDER)
        with open(OUT_SHOULDER, 'r', encoding='utf-8') as f:
            has_dashed_sh = 'stroke-dasharray' in f.read()
        print(f'  wrote {OUT_SHOULDER} ({size_sh:,} bytes, dashed={has_dashed_sh})')

    # Important: do NOT save the document. The .FCStd is owned by build_freecad.py
    # and the shoulder agent. Closing without saving discards our scaffolding.
    App.closeDocument(doc_name)
    print('done.')


if __name__ == '__main__':
    main()
