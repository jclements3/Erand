"""Check whether the hand-drawn brown curve in erand47jc.svg
penetrates any of the R=12 buffer circles in that same file.

Everything stays in the Inkscape-translated coordinate frame.
"""
import re
import math

with open("erand47jc.svg") as fh:
    txt = fh.read()

circle_re = re.compile(r'<circle\b[^>]*?cx="([-0-9.eE]+)"[^>]*?cy="([-0-9.eE]+)"[^>]*?r="([-0-9.eE]+)"', re.S)
circles = [(float(cx), float(cy), float(r)) for cx, cy, r in circle_re.findall(txt)]
print(f"circles: {len(circles)}")

paths = re.findall(r'<path\b([^>]*?)/>', txt, re.S | re.I)
brown_d = None
for attrs in paths:
    if 'stroke="#8b4513"' in attrs.lower():
        md = re.search(r'\bd="([^"]+)"', attrs, re.S)
        if md:
            brown_d = md.group(1)
            break
d = brown_d
print(f"brown d (first 120 chars): {d[:120]!r}")


def tokenize(d):
    out = []
    i = 0
    num_re = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?')
    while i < len(d):
        ch = d[i]
        if ch.isalpha():
            out.append(ch)
            i += 1
        elif ch in ' ,\t\n':
            i += 1
        else:
            m = num_re.match(d, i)
            if m is None:
                i += 1
                continue
            out.append(float(m.group()))
            i = m.end()
    return out


toks = tokenize(d)

segs = []  # list of ('L', (x0,y0), (x1,y1)) or ('C', p0, p1, p2, p3)
cx, cy = 0.0, 0.0
start_x, start_y = 0.0, 0.0
cmd = None
i = 0
prev_cmd = None

def num(j):
    return toks[j]

while i < len(toks):
    t = toks[i]
    if isinstance(t, str):
        cmd = t
        i += 1
    # consume args based on cmd
    if cmd in ('m', 'M'):
        x, y = num(i), num(i+1); i += 2
        if cmd == 'm':
            cx += x; cy += y
        else:
            cx, cy = x, y
        start_x, start_y = cx, cy
        # subsequent pairs are implicit line-to of same case
        cmd = 'l' if cmd == 'm' else 'L'
    elif cmd in ('l', 'L'):
        x, y = num(i), num(i+1); i += 2
        nx, ny = (cx + x, cy + y) if cmd == 'l' else (x, y)
        segs.append(('L', (cx, cy), (nx, ny)))
        cx, cy = nx, ny
    elif cmd in ('h', 'H'):
        x = num(i); i += 1
        nx = cx + x if cmd == 'h' else x
        segs.append(('L', (cx, cy), (nx, cy)))
        cx = nx
    elif cmd in ('v', 'V'):
        y = num(i); i += 1
        ny = cy + y if cmd == 'v' else y
        segs.append(('L', (cx, cy), (cx, ny)))
        cy = ny
    elif cmd in ('c', 'C'):
        x1, y1, x2, y2, x3, y3 = (num(i+k) for k in range(6)); i += 6
        if cmd == 'c':
            p1 = (cx + x1, cy + y1)
            p2 = (cx + x2, cy + y2)
            p3 = (cx + x3, cy + y3)
        else:
            p1, p2, p3 = (x1, y1), (x2, y2), (x3, y3)
        segs.append(('C', (cx, cy), p1, p2, p3))
        cx, cy = p3
    elif cmd in ('z', 'Z'):
        segs.append(('L', (cx, cy), (start_x, start_y)))
        cx, cy = start_x, start_y
    else:
        raise ValueError(f"Unhandled cmd {cmd} at token {i}")

print(f"segments: {len(segs)}  (Line={sum(1 for s in segs if s[0]=='L')}, Cubic={sum(1 for s in segs if s[0]=='C')})")


def sample_seg(seg, n=200):
    if seg[0] == 'L':
        _, p0, p1 = seg
        return [(p0[0] + (p1[0]-p0[0])*t, p0[1] + (p1[1]-p0[1])*t) for t in (k/n for k in range(n+1))]
    _, p0, p1, p2, p3 = seg
    pts = []
    for k in range(n+1):
        t = k/n
        u = 1 - t
        x = u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts


crossings = []  # (seg_idx, buffer_idx, min_dist)
for si, seg in enumerate(segs):
    pts = sample_seg(seg, n=400)
    for bi, (bcx, bcy, br) in enumerate(circles):
        md = min(math.hypot(px-bcx, py-bcy) for px, py in pts)
        if md < br - 1e-6:
            crossings.append((si, bi, md, (bcx, bcy)))

print()
if not crossings:
    # report worst-case min distances instead
    print("No buffer penetrated. Tightest clearances:")
    all_min = []
    for si, seg in enumerate(segs):
        pts = sample_seg(seg, n=400)
        for bi, (bcx, bcy, br) in enumerate(circles):
            md = min(math.hypot(px-bcx, py-bcy) for px, py in pts)
            all_min.append((md, si, bi, (bcx, bcy), br))
    all_min.sort()
    for md, si, bi, (bcx, bcy), br in all_min[:10]:
        print(f"  seg {si:>2}  circle#{bi:<2} @ ({bcx:8.3f},{bcy:8.3f}) r={br}  min_d={md:7.3f}  ({md-br:+.3f} from edge)")
else:
    print(f"BROWN CROSSES {len(set(b for _, b, _, _ in crossings))} buffer circles:")
    by_buf = {}
    for si, bi, md, bc in crossings:
        by_buf.setdefault(bi, []).append((si, md, bc))
    for bi, rows in sorted(by_buf.items()):
        bcx, bcy = rows[0][2]
        md = min(r[1] for r in rows)
        segset = sorted({r[0] for r in rows})
        # untranslate back to authoring frame
        print(f"  circle#{bi} @ inkscape({bcx:8.3f},{bcy:8.3f}) = authoring({bcx+51.9:8.3f},{bcy+121.64:8.3f})  min_d={md:6.3f} mm  (deficit {12.0-md:5.3f})  segs={segset}")

# top 10 tightest clearances overall
all_min = []
for si, seg in enumerate(segs):
    pts = sample_seg(seg, n=400)
    for bi, (bcx, bcy, br) in enumerate(circles):
        md = min(math.hypot(px-bcx, py-bcy) for px, py in pts)
        all_min.append((md, si, bi, (bcx, bcy), br))
all_min.sort()
print("\nTop 10 tightest (any sign):")
for md, si, bi, (bcx, bcy), br in all_min[:10]:
    print(f"  seg {si}  circle#{bi} @ ink({bcx:8.3f},{bcy:8.3f}) = auth({bcx+51.9:8.3f},{bcy+121.64:8.3f})  min_d={md:7.3f}  ({md-br:+.3f} from edge)")
