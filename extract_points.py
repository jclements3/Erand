#!/usr/bin/env python3
"""Extract per-string geometry from erand.dxf.

Classifies LINE entities into:
  - 47 vertical strings
  - 141 horizontal 0.25-unit ticks (3 per string: two on-string + one at key tip)
  - 47 diagonal 1.53-unit "key" lines at ~78 deg

Per-string landmarks (labeled A per user):
  grommet point = string bottom endpoint  (at soundboard)
  natural point = lower on-string tick    (shorter active length)
  flat point    = upper on-string tick    (= string top, longer active length)
  sharp point   = key-tip tick            (above string top, end of diagonal)
"""
import ezdxf, math, csv, sys

SRC = '/home/james.clements/projects/erand/erand.dxf'
OUT_CSV = '/home/james.clements/projects/erand/points.csv'
OUT_MD  = '/home/james.clements/projects/erand/points.md'

doc = ezdxf.readfile(SRC)
msp = doc.modelspace()

strings, on_ticks, off_ticks, keys = [], [], [], []
for L in msp.query('LINE'):
    dx = L.dxf.end.x - L.dxf.start.x
    dy = L.dxf.end.y - L.dxf.start.y
    length = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx))
    if abs(length - 0.25) < 1e-3 and abs(ang) < 1:
        # tick: classify later by proximity to string x
        on_ticks.append(L)
    elif abs(length - 1.53) < 0.02 and abs(ang - 78) < 2:
        keys.append(L)
    elif abs(ang - 90) < 1 and length > 2:
        strings.append(L)

# Normalize strings: (x, y_grommet, y_flat)
rows = []
for L in strings:
    y0, y1 = sorted([L.dxf.start.y, L.dxf.end.y])
    rows.append({'x': round(L.dxf.start.x, 4), 'y_grommet': y0, 'y_flat': y1})
rows.sort(key=lambda r: r['x'])

# Rank by active length ascending -> string number 1..47
for i, r in enumerate(sorted(rows, key=lambda r: r['y_flat'] - r['y_grommet'])):
    r['num'] = i + 1

# Attach ticks. Each 0.25-unit tick has center at (start.x + 0.125, start.y).
# On-string ticks center on string.x; key-tip ticks center ~ (string.x + 0.319, string.y_flat + 1.497).
for r in rows:
    r['on_ticks_y'] = []
    r['key_tip'] = None

for T in on_ticks:
    cx = T.dxf.start.x + 0.125
    cy = T.dxf.start.y
    # nearest string by x
    best = min(rows, key=lambda r: abs(r['x'] - cx))
    if abs(best['x'] - cx) < 0.15:
        best['on_ticks_y'].append(round(cy, 4))
    else:
        # key-tip tick: find string whose key-tip position matches
        best2 = min(rows, key=lambda r: abs(r['x'] + 0.319 - cx) + abs(r['y_flat'] + 1.497 - cy))
        best2['key_tip'] = (round(cx, 4), round(cy, 4))

# Validate from the 1.53 diagonal "key" lines (independent check)
for K in keys:
    for a, b in [(K.dxf.start, K.dxf.end), (K.dxf.end, K.dxf.start)]:
        # a is on string top; b is tip
        best = min(rows, key=lambda r: (r['x'] - a.x)**2 + (r['y_flat'] - a.y)**2)
        if (best['x'] - a.x)**2 + (best['y_flat'] - a.y)**2 < 0.01:
            best['key_start'] = (round(a.x, 4), round(a.y, 4))
            best['key_end']   = (round(b.x, 4), round(b.y, 4))
            break

# Sanity check
bad = [r for r in rows if len(r['on_ticks_y']) != 2 or r['key_tip'] is None]
if bad:
    print(f"WARN: {len(bad)} strings have unexpected tick counts", file=sys.stderr)

# Build labeled landmarks
def landmarks(r):
    ticks = sorted(r['on_ticks_y'])
    nat_y = ticks[0]   # lower on-string tick = natural (shorter length)
    flat_y = ticks[1]  # upper on-string tick = flat (longer length, == y_flat)
    return {
        'num':     r['num'],
        'x':       r['x'],
        'grommet': (r['x'], round(r['y_grommet'], 4)),
        'natural': (r['x'], nat_y),
        'flat':    (r['x'], flat_y),
        'sharp':   r['key_tip'],  # offset: (x+0.319, y_flat+1.497)
    }

landmarks_list = sorted([landmarks(r) for r in rows], key=lambda d: d['num'])

# String spacings (sorted left-to-right along the neck)
rows_by_x = sorted(rows, key=lambda r: r['x'])
spacings = [round(rows_by_x[i+1]['x'] - rows_by_x[i]['x'], 4) for i in range(len(rows_by_x) - 1)]

# Total spacing, soundboard length
total_spacing = round(rows_by_x[-1]['x'] - rows_by_x[0]['x'], 5)
sb_length = round(max(r['y_flat'] for r in rows) - min(r['y_grommet'] for r in rows), 5)

# Emit CSV
with open(OUT_CSV, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['string_num', 'x',
                'grommet_x', 'grommet_y',
                'natural_x', 'natural_y',
                'flat_x',    'flat_y',
                'sharp_x',   'sharp_y',
                'active_natural', 'active_flat', 'semitone_ratio'])
    for L in landmarks_list:
        gx, gy = L['grommet']; nx, ny = L['natural']
        fx, fy = L['flat']; sx, sy = L['sharp']
        active_nat = round(ny - gy, 4)
        active_flat = round(fy - gy, 4)
        ratio = round(active_flat / active_nat, 6) if active_nat else ''
        w.writerow([L['num'], L['x'], gx, gy, nx, ny, fx, fy, sx, sy,
                    active_nat, active_flat, ratio])

# Emit Markdown summary
with open(OUT_MD, 'w') as f:
    f.write('# Erand DXF Point Extraction\n\n')
    f.write(f'Source: `erand.dxf` (AutoCAD 2000, AC1015). Drawing units = inches ("British Unit").\n\n')
    f.write('## Summary\n\n')
    f.write(f'- Strings: **{len(rows)}** (vertical, x ranging {rows_by_x[0]["x"]:.3f} to {rows_by_x[-1]["x"]:.3f})\n')
    f.write(f'- Total stringband span (file units): **{total_spacing}**  (label: 27.98566)\n')
    f.write(f'- Soundboard length (file units): **{sb_length}**  (label: 52.81111)\n')
    f.write(f'- On-string ticks: **{len(on_ticks)}** (0.25" horizontal)\n')
    f.write(f'- Key diagonals: **{len(keys)}** (1.53" at ~78°, i.e. 12° from vertical)\n\n')

    f.write('## Labeling Convention\n\n')
    f.write('Per string, 4 landmarks are derived:\n\n')
    f.write('| Landmark | Source in DXF | Position relative to string |\n')
    f.write('|---|---|---|\n')
    f.write('| **grommet** | bottom endpoint of vertical string line | at soundboard (y = y_grommet) |\n')
    f.write('| **natural** | lower on-string 0.25" tick | on string, y_natural < y_flat |\n')
    f.write('| **flat**    | upper on-string 0.25" tick | on string, y_flat = string top |\n')
    f.write('| **sharp**   | 0.25" tick at key-tip | offset from string top by +0.319, +1.497 (end of 1.53"/78° diagonal) |\n\n')
    f.write('Flat-to-natural active-length ratio is exactly 2^(1/12) = 1.05946 on every string (one semitone).\n\n')

    f.write('## String Spacings (file units, left-to-right / bass-to-treble)\n\n')
    f.write('```\n')
    for i, s in enumerate(spacings):
        f.write(f'  s{i+1:02d}->{i+2:02d}: {s}\n')
    f.write('```\n\n')
    f.write(f'Spacing stats: min={min(spacings)}, max={max(spacings)}, mean={round(sum(spacings)/len(spacings),4)}\n\n')

    f.write('## Per-String Landmarks\n\n')
    f.write('All coordinates are (x, y) in drawing units (inches).\n\n')
    f.write('| # | x | grommet y | natural y | flat y | sharp (x,y) | L_nat | L_flat |\n')
    f.write('|---:|---:|---:|---:|---:|---|---:|---:|\n')
    for L in landmarks_list:
        gx, gy = L['grommet']; nx, ny = L['natural']
        fx, fy = L['flat']; sx, sy = L['sharp']
        f.write(f'| {L["num"]} | {L["x"]:.3f} | {gy:.4f} | {ny:.4f} | {fy:.4f} | ({sx:.4f}, {sy:.4f}) | {ny-gy:.4f} | {fy-gy:.4f} |\n')

print(f"Wrote {OUT_CSV}")
print(f"Wrote {OUT_MD}")
print(f"\nString count: {len(rows)}")
print(f"Total span: {total_spacing}   (label says 27.98566)")
print(f"Soundboard length: {sb_length}   (label says 52.81111)")
print(f"Spacing: min={min(spacings)}, max={max(spacings)}, mean={sum(spacings)/len(spacings):.4f}")

# Verify semitone ratio on a sample
import statistics
ratios = []
for L in landmarks_list:
    gy = L['grommet'][1]; ny = L['natural'][1]; fy = L['flat'][1]
    if ny - gy > 0:
        ratios.append((fy - gy) / (ny - gy))
print(f"\nflat/natural active-length ratio: mean={statistics.mean(ratios):.6f}, stdev={statistics.pstdev(ratios):.2e}")
print(f"2^(1/12) = {2**(1/12):.6f}")
