"""Draw the show's cover art: an abstract die with routed traces, title and tagline."""
import random
import sys
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1] if len(sys.argv) > 1 else "cover.png"
S = 1400
BG = (16, 22, 30)
DIE = (28, 38, 50)
TRACE = (64, 92, 116)
ACCENT = (244, 166, 72)
TEXT = (238, 241, 245)
MUTED = (150, 168, 186)

img = Image.new("RGB", (S, S), BG)
d = ImageDraw.Draw(img)

# Die outline with pads
x0, y0, x1, y1 = 170, 150, S - 170, 830
d.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=DIE, outline=TRACE, width=4)
for i in range(14):
    px = x0 + 60 + i * (x1 - x0 - 120) / 13
    d.rectangle([px - 9, y0 - 26, px + 9, y0 - 6], fill=TRACE)
    d.rectangle([px - 9, y1 + 6, px + 9, y1 + 26], fill=TRACE)

# Manhattan-routed traces between grid points
random.seed(7)
grid = 40
cols = [x0 + 60 + k * grid for k in range(int((x1 - x0 - 120) / grid) + 1)]
rows = [y0 + 60 + k * grid for k in range(int((y1 - y0 - 120) / grid) + 1)]
for _ in range(46):
    cx, cy = random.choice(cols), random.choice(rows)
    pts = [(cx, cy)]
    for step in range(random.randint(2, 5)):
        if step % 2 == 0:
            cx = random.choice(cols)
        else:
            cy = random.choice(rows)
        pts.append((cx, cy))
    d.line(pts, fill=TRACE, width=5, joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7], fill=TRACE)

# One highlighted path: the signal that "signs off"
path = [(cols[1], rows[-2]), (cols[5], rows[-2]), (cols[5], rows[3]), (cols[12], rows[3]), (cols[12], rows[8]), (cols[-2], rows[8])]
d.line(path, fill=ACCENT, width=9, joint="curve")
for p in (path[0], path[-1]):
    d.ellipse([p[0] - 14, p[1] - 14, p[0] + 14, p[1] + 14], fill=ACCENT)

title_font = ImageFont.truetype("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf", 196) if __import__("os").path.exists("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf") else ImageFont.truetype("/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf", 196)
tag_font = ImageFont.truetype("/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf", 64)

d.text((S / 2, 1030), "The Signoff", font=title_font, fill=TEXT, anchor="mm")
d.rectangle([S / 2 - 90, 1160, S / 2 + 90, 1168], fill=ACCENT)
d.text((S / 2, 1250), "AI in chip design, weekly", font=tag_font, fill=MUTED, anchor="mm")

img.save(out, "PNG")
print("wrote", out)
