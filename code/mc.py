"""
The most atomic way to run Monte Carlo retirement simulation in pure, dependency-free Python.
Simulates N random financial lifetimes, computes outcome distributions, and renders
a spaghetti chart of all paths as an SVG file. No numpy, no matplotlib, no pandas.
The contents of this file is everything algorithmically needed for MC retirement planning.
Everything else is just efficiency.
Art project inspired by @karpathy's microgpt.
"""

import math     # for math.log, math.cos, math.sqrt, math.pi, math.exp
import random   # for random.random, random.seed
import argparse # for argparse.ArgumentParser

# ---------------------------------------------------------------------------
# CLI arguments — the 5 atoms of the MC retirement problem
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="micromc: atomic Monte Carlo retirement simulator")
parser.add_argument('--start',   type=float, default=50000, help='Starting savings ($)')
parser.add_argument('--monthly', type=float, default=500,   help='Monthly contribution ($)')
parser.add_argument('--years',   type=int,   default=35,    help='Years to retirement')
parser.add_argument('--mean',    type=float, default=0.07,  help='Mean annual return')
parser.add_argument('--std',     type=float, default=0.15,  help='Std dev of annual return (volatility)')
parser.add_argument('--n_sims',  type=int,   default=1000,  help='Number of simulated lifetimes')
parser.add_argument('--goal',    type=float, default=800000,help='Retirement goal ($)')
parser.add_argument('--seed',    type=int,   default=42,    help='Random seed')
parser.add_argument('--out',     type=str,   default='micromc.html', help='Output chart file')
args = parser.parse_args()
random.seed(args.seed)

# ---------------------------------------------------------------------------
# Element 1: Random sampling — Box-Muller transform for normal distribution
# This is where randomness enters. Without this, it's just compound interest.
# ---------------------------------------------------------------------------
def randn():
    """Sample from N(0,1) using Box-Muller. Two uniform randoms → one Gaussian."""
    u1 = random.random()
    u2 = random.random()
    while u1 == 0: u1 = random.random()  # avoid log(0)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

# ---------------------------------------------------------------------------
# Element 2: The evaluation function f(x)
# This IS the retirement problem. One random sequence of returns → one final balance.
# Returns the full path (balance at each year) for visualization.
# ---------------------------------------------------------------------------
def simulate_path(start, monthly, years, mean, std):
    """Simulate one financial lifetime. Returns list of (years+1) balances."""
    path = [start]
    balance = start
    for _ in range(years):
        r = mean + std * randn()               # xᵢ: one random annual return
        balance = balance * (1 + r) + monthly * 12  # f: compound + contribute
        balance = max(0.0, balance)             # can't go below zero
        path.append(balance)
    return path

# ---------------------------------------------------------------------------
# Element 3: Run N simulations — the aggregation operator
# ---------------------------------------------------------------------------
print(f"micromc | {args.n_sims} simulations × {args.years} years")
print(f"start: ${args.start:,.0f} | monthly: ${args.monthly:,.0f} | "
      f"return: {args.mean:.1%} ± {args.std:.1%} | goal: ${args.goal:,.0f}")
print()

paths = []
finals = []
for i in range(args.n_sims):
    path = simulate_path(args.start, args.monthly, args.years, args.mean, args.std)
    paths.append(path)
    finals.append(path[-1])

finals_sorted = sorted(finals)

# ---------------------------------------------------------------------------
# Element 4: Statistics — extract signal from noise
# ---------------------------------------------------------------------------
def percentile(sorted_vals, p):
    """p in [0,1]. Linear interpolation between nearest ranks."""
    idx = p * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac

def fmt(v):
    """Format dollar amount."""
    if v >= 1e6: return f"${v/1e6:.2f}M"
    return f"${v:,.0f}"

N = args.n_sims
mean_final = sum(finals) / N
median = percentile(finals_sorted, 0.50)
p10    = percentile(finals_sorted, 0.10)
p25    = percentile(finals_sorted, 0.25)
p75    = percentile(finals_sorted, 0.75)
p90    = percentile(finals_sorted, 0.90)
worst  = finals_sorted[0]
best   = finals_sorted[-1]
p_goal = sum(1 for v in finals if v >= args.goal) / N

# deterministic comparison (the lie of constant returns)
det = args.start
for _ in range(args.years):
    det = det * (1 + args.mean) + args.monthly * 12

print(f"--- deterministic (the lie) ---")
print(f"constant {args.mean:.0%} every year: {fmt(det)}")
print()
print(f"--- monte carlo (the truth) ---")
print(f"{'median':>12s}: {fmt(median)}")
print(f"{'mean':>12s}: {fmt(mean_final)}")
print(f"{'10th %ile':>12s}: {fmt(p10)}")
print(f"{'25th %ile':>12s}: {fmt(p25)}")
print(f"{'75th %ile':>12s}: {fmt(p75)}")
print(f"{'90th %ile':>12s}: {fmt(p90)}")
print(f"{'worst':>12s}: {fmt(worst)}")
print(f"{'best':>12s}: {fmt(best)}")
print(f"{'P(≥ goal)':>12s}: {p_goal:.1%}")
print()

# ---------------------------------------------------------------------------
# Element 5: ASCII spaghetti chart — see the fan in your terminal
# ---------------------------------------------------------------------------
CHART_W, CHART_H = 80, 24
# compute percentile paths for the chart
pct_paths = {}
for pct in [0.10, 0.25, 0.50, 0.75, 0.90]:
    pct_path = []
    for yr in range(args.years + 1):
        year_vals = sorted([paths[s][yr] for s in range(N)])
        pct_path.append(percentile(year_vals, pct))
    pct_paths[pct] = pct_path

chart_max = max(pct_paths[0.90])  # cap at p90 for readability
chart_min = 0

print(f"--- spaghetti chart (percentile bands) ---")
print(f"  {fmt(chart_max):>10s} ┐")
grid = [[' '] * CHART_W for _ in range(CHART_H)]

# plot percentile lines
symbols = {0.10: '░', 0.25: '▒', 0.50: '█', 0.75: '▒', 0.90: '░'}
for pct, sym in symbols.items():
    path = pct_paths[pct]
    for yr in range(args.years + 1):
        col = int(yr / args.years * (CHART_W - 1))
        val = min(path[yr], chart_max)
        row = CHART_H - 1 - int((val - chart_min) / (chart_max - chart_min) * (CHART_H - 1))
        row = max(0, min(CHART_H - 1, row))
        grid[row][col] = sym

for r in range(CHART_H):
    line = ''.join(grid[r])
    if r == 0:
        print(f"            │{line}│")
    elif r == CHART_H - 1:
        print(f"  {fmt(chart_min):>10s} ┘{line}│")
    else:
        print(f"            │{line}│")

print(f"             {'Yr 0':<{CHART_W//2}}{'Yr ' + str(args.years):>{CHART_W//2}}")
print(f"             ░ = 10th/90th   ▒ = 25th/75th   █ = median")
print()

# ---------------------------------------------------------------------------
# Histogram of final outcomes
# ---------------------------------------------------------------------------
N_BINS = 40
hist_max = percentile(finals_sorted, 0.95)
hist_min = finals_sorted[0]
bin_w = (hist_max - hist_min) / N_BINS
bins = [0] * N_BINS
for v in finals:
    bi = int((v - hist_min) / bin_w) if bin_w > 0 else 0
    bi = max(0, min(N_BINS - 1, bi))
    bins[bi] += 1
max_bin = max(bins)

print(f"--- distribution of final portfolio values ---")
HIST_H = 12
for row in range(HIST_H, 0, -1):
    threshold = row / HIST_H * max_bin
    line = ''
    for bi in range(N_BINS):
        val_center = hist_min + (bi + 0.5) * bin_w
        if bins[bi] >= threshold:
            line += '█' if val_center >= args.goal else '░'
        else:
            line += ' '
    lbl = ''
    if row == HIST_H: lbl = f'{max_bin}'
    print(f"  {lbl:>4s} │{line}│")

print(f"       └{'─' * N_BINS}┘")
tick_positions = [0, N_BINS // 4, N_BINS // 2, 3 * N_BINS // 4, N_BINS - 1]
tick_line = [' '] * (N_BINS + 8)
for tp in tick_positions:
    val = hist_min + (tp + 0.5) * bin_w
    label = fmt(val)
    pos = tp + 7
    for ci, ch in enumerate(label):
        if 0 <= pos + ci < len(tick_line):
            tick_line[pos + ci] = ch
print(''.join(tick_line))
print(f"       ░ = below goal   █ = above goal ({fmt(args.goal)})")
print()

# ---------------------------------------------------------------------------
# SVG chart generation — pure string manipulation, zero dependencies
# ---------------------------------------------------------------------------
SVG_W, SVG_H = 800, 500
MARGIN = {'top': 40, 'right': 80, 'bottom': 50, 'left': 70}
PLOT_W = SVG_W - MARGIN['left'] - MARGIN['right']
PLOT_H = SVG_H - MARGIN['top'] - MARGIN['bottom']

# use p95 as chart max to avoid outlier compression
svg_max = percentile(finals_sorted, 0.95) * 1.1
svg_min = 0

def to_x(yr):
    return MARGIN['left'] + (yr / args.years) * PLOT_W

def to_y(val):
    val = min(val, svg_max)
    return MARGIN['top'] + PLOT_H * (1 - (val - svg_min) / (svg_max - svg_min))

# build SVG
svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_W} {SVG_H}" '
           f'font-family="monospace" font-size="11">')
svg.append(f'<rect width="{SVG_W}" height="{SVG_H}" fill="#fff"/>')

# plot area background
svg.append(f'<rect x="{MARGIN["left"]}" y="{MARGIN["top"]}" '
           f'width="{PLOT_W}" height="{PLOT_H}" fill="#fafafa" stroke="#e5e7eb"/>')

# grid lines and y-axis labels
n_grid = 5
for i in range(n_grid + 1):
    val = svg_min + (svg_max - svg_min) * i / n_grid
    y = to_y(val)
    svg.append(f'<line x1="{MARGIN["left"]}" y1="{y:.1f}" x2="{SVG_W - MARGIN["right"]}" '
               f'y2="{y:.1f}" stroke="#e5e7eb" stroke-width="0.5"/>')
    svg.append(f'<text x="{MARGIN["left"] - 8}" y="{y + 4:.1f}" text-anchor="end" '
               f'fill="#666" font-size="9">{fmt(val)}</text>')

# x-axis labels
step = 5 if args.years <= 20 else 10
for yr in range(0, args.years + 1, step):
    x = to_x(yr)
    y = MARGIN['top'] + PLOT_H
    svg.append(f'<text x="{x:.1f}" y="{y + 20:.1f}" text-anchor="middle" '
               f'fill="#666" font-size="9">Yr {yr}</text>')

# goal line
goal_y = to_y(args.goal)
if svg_min <= args.goal <= svg_max:
    svg.append(f'<line x1="{MARGIN["left"]}" y1="{goal_y:.1f}" '
               f'x2="{SVG_W - MARGIN["right"]}" y2="{goal_y:.1f}" '
               f'stroke="#dc2626" stroke-width="1.5" stroke-dasharray="6,4"/>')
    svg.append(f'<text x="{SVG_W - MARGIN["right"] + 4}" y="{goal_y + 4:.1f}" '
               f'fill="#dc2626" font-size="9">Goal {fmt(args.goal)}</text>')

# spaghetti paths — sample up to 500 for readability
n_draw = min(args.n_sims, 500)
draw_indices = list(range(args.n_sims))
random.shuffle(draw_indices)
draw_indices = draw_indices[:n_draw]

for si in draw_indices:
    path = paths[si]
    final = path[-1]
    # color by outcome: red → yellow → green
    t = min(final / svg_max, 1.0)
    r = int(220 - t * 180)
    g = int(80 + t * 140)
    b = int(80 - t * 40)
    points = []
    for yr in range(args.years + 1):
        x = to_x(yr)
        y = to_y(path[yr])
        points.append(f"{x:.1f},{y:.1f}")
    svg.append(f'<polyline points="{" ".join(points)}" fill="none" '
               f'stroke="rgb({r},{g},{b})" stroke-width="0.8" opacity="0.12"/>')

# percentile lines
pct_configs = [
    (0.10, '#dc2626', '1.2', '4,3', '10th'),
    (0.25, '#f97316', '1.2', '3,3', '25th'),
    (0.50, '#000000', '2.5', '',     'Median'),
    (0.75, '#22c55e', '1.2', '3,3', '75th'),
    (0.90, '#16a34a', '1.2', '4,3', '90th'),
]

for pct, color, width, dash, label in pct_configs:
    pp = pct_paths[pct]
    points = []
    for yr in range(args.years + 1):
        x = to_x(yr)
        y = to_y(pp[yr])
        points.append(f"{x:.1f},{y:.1f}")
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    svg.append(f'<polyline points="{" ".join(points)}" fill="none" '
               f'stroke="{color}" stroke-width="{width}"{dash_attr}/>')
    # label at the end
    end_y = to_y(pp[-1])
    svg.append(f'<text x="{SVG_W - MARGIN["right"] + 4}" y="{end_y + 4:.1f}" '
               f'fill="{color}" font-size="9" font-weight="bold">{label}</text>')

# deterministic line
det_path = [args.start]
d = args.start
for _ in range(args.years):
    d = d * (1 + args.mean) + args.monthly * 12
    det_path.append(d)
det_points = []
for yr in range(args.years + 1):
    x = to_x(yr)
    y = to_y(det_path[yr])
    det_points.append(f"{x:.1f},{y:.1f}")
svg.append(f'<polyline points="{" ".join(det_points)}" fill="none" '
           f'stroke="#999" stroke-width="1.5" stroke-dasharray="8,4"/>')
det_end_y = to_y(det_path[-1])
svg.append(f'<text x="{SVG_W - MARGIN["right"] + 4}" y="{det_end_y + 4:.1f}" '
           f'fill="#999" font-size="9">Det {fmt(det_path[-1])}</text>')

# title
svg.append(f'<text x="{MARGIN["left"]}" y="20" font-size="14" font-weight="bold">'
           f'micromc: {args.n_sims} simulated lifetimes</text>')
svg.append(f'<text x="{MARGIN["left"]}" y="34" font-size="10" fill="#666">'
           f'${args.start:,.0f} start · ${args.monthly:,.0f}/mo · '
           f'{args.mean:.0%} ± {args.std:.0%} · {args.years} years · '
           f'P(≥ {fmt(args.goal)}) = {p_goal:.0%}</text>')

svg.append('</svg>')

# wrap in HTML
html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>micromc — {args.n_sims} simulated lifetimes</title>
<style>
  body {{ font-family: 'IBM Plex Mono', monospace; max-width: 860px; margin: 40px auto; padding: 0 20px; color: #000; }}
  h1 {{ font-size: 18px; margin-bottom: 4px; }}
  .sub {{ font-size: 12px; color: #666; margin-bottom: 24px; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; font-size: 12px; }}
  .stat {{ border: 1px solid #000; padding: 10px; box-shadow: 2px 2px 0px #000; }}
  .stat .label {{ font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat .value {{ font-size: 18px; font-weight: bold; margin-top: 4px; }}
  .pos {{ color: #16a34a; }}
  .neg {{ color: #dc2626; }}
  svg {{ width: 100%; height: auto; border: 1px solid #e5e7eb; }}
  .footer {{ font-size: 10px; color: #999; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }}
  .code {{ background: #fafafa; border: 1px solid #e5e7eb; padding: 12px; font-size: 11px; margin: 16px 0; white-space: pre; overflow-x: auto; }}
</style>
</head><body>
<h1>micromc: {args.n_sims} simulated lifetimes</h1>
<div class="sub">pure python · zero dependencies · inspired by karpathy's microgpt</div>

<div class="stats">
  <div class="stat">
    <div class="label">Median</div>
    <div class="value">{fmt(median)}</div>
  </div>
  <div class="stat">
    <div class="label">10th %ile</div>
    <div class="value neg">{fmt(p10)}</div>
  </div>
  <div class="stat">
    <div class="label">90th %ile</div>
    <div class="value pos">{fmt(p90)}</div>
  </div>
  <div class="stat">
    <div class="label">P(≥ {fmt(args.goal)})</div>
    <div class="value {'pos' if p_goal > 0.5 else 'neg'}">{p_goal:.1%}</div>
  </div>
</div>

{''.join(svg)}

<div class="stats">
  <div class="stat">
    <div class="label">Deterministic (lie)</div>
    <div class="value">{fmt(det)}</div>
  </div>
  <div class="stat">
    <div class="label">Mean (skewed)</div>
    <div class="value">{fmt(mean_final)}</div>
  </div>
  <div class="stat">
    <div class="label">Worst case</div>
    <div class="value neg">{fmt(worst)}</div>
  </div>
  <div class="stat">
    <div class="label">Best case</div>
    <div class="value pos">{fmt(best)}</div>
  </div>
</div>

<div class="code">E[f(X)] ≈ (1/N) Σ f(xᵢ)

Ω  = all possible {args.years}-year return sequences
f  = compound: balance × (1 + r) + contributions
xᵢ = one random sequence ~ N({args.mean:.0%}, {args.std:.0%}) per year
N  = {args.n_sims:,} simulations
Ê  = distribution of final portfolio values</div>

<div class="footer">
  micromc · the most atomic Monte Carlo retirement simulator · pure python, zero dependencies
</div>
</body></html>"""

with open(args.out, 'w') as f:
    f.write(html)

print(f"chart saved to {args.out}")
