#!/usr/bin/env python3
"""Turn a rendered emblem on a soft gradient background into a circular badge PNG.

    python3 tools/make_badge.py backups/<render>.jpg assets/img/logo-full.png [--no-rim]

Fits the background as a smooth gradient from the border pixels, extends the canvas
with that gradient so the whole emblem fits inside a circle, masks the circle with a
soft edge, and (by default) draws a thin brass rim. Needs Pillow only. Regenerate the
smaller sizes afterwards (160 px for nav/footer, 600 px PNG + WebP for the About card).
"""
import sys, math, colorsys
from PIL import Image, ImageDraw, ImageFilter

src_path, out_path = sys.argv[1], sys.argv[2]
rim = '--no-rim' not in sys.argv
src = Image.open(src_path).convert('RGB'); W, H = src.size; p = src.load()

# --- background model: quadratic surface per channel, fitted to background-looking border pixels
samples = []
for y in range(H):
    for x in range(W):
        if x < 36 or x > W - 37 or y < 36 or y > H - 37:
            r, g, b = p[x, y]; h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if l >= 0.45 and s <= 0.45: samples.append((x, y, r, g, b))
def fit(ch):
    rows, rhs = [], []
    for x, y, r, g, b in samples:
        X, Y = x / W, y / H; rows.append([1, X, Y, X * X, Y * Y, X * Y]); rhs.append((r, g, b)[ch])
    n = 6
    A = [[sum(rw[i] * rw[j] for rw in rows) for j in range(n)] for i in range(n)]
    B = [sum(rw[i] * v for rw, v in zip(rows, rhs)) for i in range(n)]
    for i in range(n):
        piv = max(range(i, n), key=lambda k: abs(A[k][i])); A[i], A[piv] = A[piv], A[i]; B[i], B[piv] = B[piv], B[i]
        for k in range(i + 1, n):
            f = A[k][i] / A[i][i]
            for j in range(i, n): A[k][j] -= f * A[i][j]
            B[k] -= f * B[i]
    c = [0] * n
    for i in range(n - 1, -1, -1): c[i] = (B[i] - sum(A[i][j] * c[j] for j in range(i + 1, n))) / A[i][i]
    return c
coef = [fit(ch) for ch in range(3)]
def bg(x, y):
    X, Y = x / W, y / H; basis = (1, X, Y, X * X, Y * Y, X * Y)
    return tuple(max(0, min(255, round(sum(c * b for c, b in zip(coef[ch], basis))))) for ch in range(3))

# --- emblem extent: pixels that differ clearly from the modelled background (ignores the soft shadow)
pts = []
for y in range(0, H, 2):
    for x in range(0, W, 2):
        r, g, b = p[x, y]; er, eg, eb = bg(x, y)
        if math.sqrt((r - er) ** 2 + (g - eg) ** 2 + (b - eb) ** 2) > 60: pts.append((x, y))
cx = (min(x for x, y in pts) + max(x for x, y in pts)) / 2
cy = (min(y for x, y in pts) + max(y for x, y in pts)) / 2
R = int(max(math.hypot(x - cx, y - cy) for x, y in pts) * 1.06); S = 2 * R + 2
print(f'emblem centre ({cx:.0f},{cy:.0f}) -> badge radius {R}px, canvas {S}px')

# --- canvas of extrapolated gradient, source centred on the emblem
canvas = Image.new('RGB', (S, S)); cp = canvas.load()
dx, dy = int(round(S / 2 - cx)), int(round(S / 2 - cy))
for y in range(S):
    for x in range(S): cp[x, y] = bg(x - dx, y - dy)
canvas.paste(src, (dx, dy))

# --- circular mask with a soft edge, optional brass rim
out = canvas.convert('RGBA')
m = Image.new('L', (S, S), 0); ImageDraw.Draw(m).ellipse((1, 1, S - 2, S - 2), fill=255)
out.putalpha(m.filter(ImageFilter.GaussianBlur(1.0)))
if rim:
    d = ImageDraw.Draw(out); w = max(4, S // 120)
    d.ellipse((w / 2, w / 2, S - 1 - w / 2, S - 1 - w / 2), outline=(150, 116, 50, 255), width=w)
    d.ellipse((w + 1, w + 1, S - 2 - w, S - 2 - w), outline=(214, 182, 110, 255), width=max(1, w // 3))
out.save(out_path, optimize=True)
print('saved', out_path)
