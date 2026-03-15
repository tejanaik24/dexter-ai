#!/usr/bin/env python3
"""
Dexter HUD v2 — Bigger orb, hidden when idle, appears on listening/speaking
"""
import tkinter as tk
import json
import math
import time
from pathlib import Path

HUD_STATE_FILE = Path.home() / ".config/jarvis/hud_state.json"

W, H = 500, 500
CX, CY = W // 2, H // 2

root = tk.Tk()
root.title("Dexter")
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
root.geometry(f"{W}x{H}+{sw-W-10}+{sh-H-50}")
root.overrideredirect(True)
root.wm_attributes("-topmost", True)
root.wm_attributes("-alpha", 0.0)   # start hidden
root.configure(bg="#04060E")

canvas = tk.Canvas(root, width=W, height=H, bg="#04060E", highlightthickness=0)
canvas.pack()

# Drag
_drag = {}
def on_press(e): _drag['x'] = e.x; _drag['y'] = e.y
def on_drag(e):
    x = root.winfo_x() + e.x - _drag['x']
    y = root.winfo_y() + e.y - _drag['y']
    root.geometry(f"+{x}+{y}")
def on_right(e): root.destroy()
canvas.bind("<ButtonPress-1>", on_press)
canvas.bind("<B1-Motion>", on_drag)
canvas.bind("<ButtonPress-3>", on_right)

t0 = time.time()
state = "idle"
rms = 0.0
brightness = 0.3
ring_angles = [0.0, 0.0, 0.0]
waveform = [0.0] * 32
current_alpha = 0.0
target_alpha = 0.0

def read_state():
    global state, rms
    try:
        if HUD_STATE_FILE.exists():
            d = json.loads(HUD_STATE_FILE.read_text())
            state = d.get("state", "idle")
            rms = float(d.get("rms", 0))
    except:
        pass

def lerp(a, b, t):
    return a + (b - a) * t

def hsv_to_hex(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, min(1.0, max(0.0, v)))
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

def draw():
    global brightness, ring_angles, waveform, state, rms, current_alpha, target_alpha
    t = time.time() - t0

    read_state()

    # Show/hide based on state
    target_alpha = 0.0 if state == "idle" else 0.95
    current_alpha = lerp(current_alpha, target_alpha, 0.15)
    root.wm_attributes("-alpha", current_alpha)

    if current_alpha < 0.02:
        root.after(50, draw)
        return

    canvas.delete("all")

    rms_norm = min(1.0, rms / 8000.0)
    speed_mult = {"listening": 1.8, "speaking": 2.5}.get(state, 0.5)

    # Target brightness
    if state == "listening":
        tb = 0.65 + rms_norm * 0.35 + math.sin(t * 5) * 0.05
    else:  # speaking
        tb = 0.7 + math.sin(t * 4) * 0.15

    brightness = lerp(brightness, tb, 0.12)

    # Outer decorative rings
    canvas.create_oval(CX-235, CY-235, CX+235, CY+235,
                      outline=hsv_to_hex(0.6, 0.8, 0.15), width=1)
    canvas.create_oval(CX-240, CY-240, CX+240, CY+240,
                      outline=hsv_to_hex(0.6, 0.8, 0.1), width=1)

    # Tick marks
    for i in range(72):
        angle = math.radians(i * 5)
        r1 = 228 if i % 6 == 0 else 232
        r2 = 238
        col = hsv_to_hex(0.6, 0.8, 0.25 if i % 6 == 0 else 0.12)
        x1 = CX + math.cos(angle) * r1
        y1 = CY + math.sin(angle) * r1
        x2 = CX + math.cos(angle) * r2
        y2 = CY + math.sin(angle) * r2
        canvas.create_line(x1, y1, x2, y2, fill=col, width=1)

    # Rotating arc rings
    ring_cfgs = [
        {"r": 195, "speed": 0.4,  "gap": 90,  "h": 0.60, "s": 0.9},
        {"r": 175, "speed": -0.6, "gap": 70,  "h": 0.62, "s": 0.85},
        {"r": 155, "speed": 0.9,  "gap": 50,  "h": 0.58, "s": 0.95},
    ]
    for i, cfg in enumerate(ring_cfgs):
        ring_angles[i] += cfg["speed"] * speed_mult * 0.025
        angle = ring_angles[i]
        gap_rad = math.radians(cfg["gap"])
        steps = 120
        col = hsv_to_hex(cfg["h"], cfg["s"], brightness * 0.85)
        pts = []
        for j in range(steps + 1):
            a = angle + (j / steps) * (2 * math.pi - gap_rad)
            x = CX + math.cos(a) * cfg["r"]
            y = CY + math.sin(a) * cfg["r"]
            pts.append((x, y))
        for j in range(len(pts) - 1):
            canvas.create_line(pts[j][0], pts[j][1], pts[j+1][0], pts[j+1][1],
                              fill=col, width=2)

    # Waveform ring
    wave_r = 130
    wc = "#00d0ff" if state == "listening" else "#80c0ff"
    for j in range(len(waveform)):
        if state == "listening":
            tw = rms_norm * (0.4 + 0.6 * abs(math.sin(t * 7 + j * 0.4)))
        else:
            tw = 0.35 + 0.45 * abs(math.sin(t * 5 + j * 0.35))
        waveform[j] = lerp(waveform[j], tw, 0.2)
        ang = math.radians(j * (360 / len(waveform)))
        amp = waveform[j] * 28
        x1 = CX + math.cos(ang) * wave_r
        y1 = CY + math.sin(ang) * wave_r
        x2 = CX + math.cos(ang) * (wave_r + amp)
        y2 = CY + math.sin(ang) * (wave_r + amp)
        canvas.create_line(x1, y1, x2, y2, fill=wc, width=2)

    # Glow layers (multiple ovals for glow effect)
    gc_h = 0.58 if state == "listening" else 0.55
    for layer in range(8, 0, -1):
        r_g = 60 + layer * 10
        v = brightness * (layer / 8) * 0.55
        col = hsv_to_hex(gc_h, 0.9, v)
        canvas.create_oval(CX-r_g, CY-r_g, CX+r_g, CY+r_g, fill=col, outline="")

    # Core orb
    orb_r = int(68 + brightness * 12)
    orb_h = 0.58 if state == "listening" else 0.55
    canvas.create_oval(CX-orb_r, CY-orb_r, CX+orb_r, CY+orb_r,
                      fill=hsv_to_hex(orb_h, 1.0, brightness * 0.85), outline="")

    # Inner bright core
    inner_r = int(32 + brightness * 16)
    canvas.create_oval(CX-inner_r, CY-inner_r, CX+inner_r, CY+inner_r,
                      fill=hsv_to_hex(0.55, 0.4, brightness * 0.95), outline="")

    # Specular highlight
    canvas.create_oval(CX-22, CY-26, CX-8, CY-12,
                      fill=hsv_to_hex(0.55, 0.15, min(1.0, brightness * 1.1)), outline="")

    # Bottom waveform bars
    bar_col = "#00a0ff" if state == "listening" else "#6090ff"
    bar_count = 28
    bar_w = 6
    bar_gap = 3
    total = bar_count * (bar_w + bar_gap)
    sx = CX - total // 2
    by = CY + 240
    for i in range(bar_count):
        bh = int(4 + waveform[i % len(waveform)] * 28 + math.sin(t*4+i*0.5)*3)
        bx = sx + i * (bar_w + bar_gap)
        canvas.create_rectangle(bx, by - bh, bx + bar_w, by + bh,
                               fill=bar_col, outline="")

    # State label
    label = "LISTENING" if state == "listening" else "SPEAKING"
    lc = "#00c8ff" if state == "listening" else "#80d0ff"
    canvas.create_text(CX, CY + 218, text=label,
                      fill=lc, font=("Courier", 13, "bold"))

    # DEXTER label top
    canvas.create_text(CX, CY - 228, text="D E X T E R",
                      fill=hsv_to_hex(0.6, 0.7, 0.3), font=("Courier", 12, "bold"))

    # Corner brackets
    for dx, dy, a1, a2 in [(-1, -1, 0, 1), (1, -1, 0, -1), (-1, 1, 0, 1), (1, 1, 0, -1)]:
        ox = CX + dx * 228
        oy = CY + dy * 228
        canvas.create_line(ox, oy, ox + dx*-20, oy, fill="#003c96", width=2)
        canvas.create_line(ox, oy, ox, oy + dy*-20, fill="#003c96", width=2)

    root.after(33, draw)

draw()
root.mainloop()
