import tkinter as tk
import threading
import math
import time
import random

# ── State colours ────────────────────────────────────────────────────────────
_STATES = {
    "idle":      {"primary": "#1a6aff", "secondary": "#0a3a8a", "label": "STANDBY"},
    "listening": {"primary": "#00e5ff", "secondary": "#007a8a", "label": "LISTENING"},
    "thinking":  {"primary": "#bf00ff", "secondary": "#6a008a", "label": "PROCESSING"},
    "speaking":  {"primary": "#00ff9f", "secondary": "#007a4a", "label": "SPEAKING"},
}

SIZE   = 260
CX     = SIZE // 2
CY     = SIZE // 2


class JarvisOverlay:
    def __init__(self):
        self._state      = "idle"
        self._running    = False
        self._root       = None
        self._canvas     = None
        self._label_var  = None
        self._thread     = None
        self._tick       = 0
        self._scan_y     = 0.0
        self._wave_vals  = [0.0] * 24
        self._particles  = []   # list of (x, y, vx, vy, life, max_life)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str):
        self._state = state if state in _STATES else "idle"
        self._show()

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self):
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-transparentcolor", "#0a0a0a")
        self._root.configure(bg="#0a0a0a")

        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        margin = 16
        self._root.geometry(f"{SIZE}x{SIZE + 22}+{sw - SIZE - margin}+{sh - SIZE - 70 - margin}")

        self._canvas = tk.Canvas(
            self._root, width=SIZE, height=SIZE,
            bg="#0a0a0a", highlightthickness=0,
        )
        self._canvas.pack()

        self._label_var = tk.StringVar(value="")
        tk.Label(
            self._root, textvariable=self._label_var,
            bg="#0a0a0a", fg="#4488ff",
            font=("Consolas", 8, "bold"),
        ).pack()

        self._root.deiconify()
        self._animate()
        self._root.mainloop()

    def _animate(self):
        if not self._running:
            return
        try:
            self._tick += 1
            self._update_particles()
            self._update_wave()
            self._draw_frame()
        except Exception:
            pass
        self._root.after(30, self._animate)   # ~33 fps

    # ── Wave & particle helpers ───────────────────────────────────────────────

    def _update_wave(self):
        state = self._state
        for i in range(len(self._wave_vals)):
            if state == "listening":
                target = random.uniform(0.2, 1.0)
            elif state == "speaking":
                target = abs(math.sin(self._tick * 0.18 + i * 0.5)) * 0.9 + 0.1
            elif state == "thinking":
                target = abs(math.sin(self._tick * 0.08 + i * 0.7)) * 0.5 + 0.05
            else:
                target = 0.05 + 0.04 * math.sin(self._tick * 0.04 + i)
            self._wave_vals[i] += (target - self._wave_vals[i]) * 0.25

    def _update_particles(self):
        if self._state in ("listening", "speaking", "thinking"):
            if random.random() < 0.35:
                angle  = random.uniform(0, 2 * math.pi)
                radius = random.uniform(72, 90)
                x = CX + radius * math.cos(angle)
                y = CY + radius * math.sin(angle)
                speed  = random.uniform(0.5, 1.8)
                vx     = -math.cos(angle) * speed
                vy     = -math.sin(angle) * speed
                life   = random.randint(18, 40)
                self._particles.append([x, y, vx, vy, life, life])
        self._particles = [
            [p[0]+p[2], p[1]+p[3], p[2], p[3], p[4]-1, p[5]]
            for p in self._particles if p[4] > 0
        ]

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw_frame(self):
        c   = self._canvas
        cfg = _STATES[self._state]
        pri = cfg["primary"]
        sec = cfg["secondary"]
        t   = self._tick

        c.delete("all")

        # ── Background circle ────────────────────────────────────────────────
        self._glow_circle(c, CX, CY, 108, sec, layers=5)
        c.create_oval(CX-105, CY-105, CX+105, CY+105,
                      fill="#080c14", outline="")

        # ── Outer ring (slow spin) ───────────────────────────────────────────
        self._draw_segmented_ring(c, CX, CY, 100, 96,
                                  segments=32, gap=4,
                                  angle_offset=t * 0.6,
                                  color=sec)

        # ── Mid ring (opposite spin, faster) ────────────────────────────────
        self._draw_segmented_ring(c, CX, CY, 88, 85,
                                  segments=16, gap=8,
                                  angle_offset=-t * 1.2,
                                  color=pri, bright_every=4)

        # ── Glowing arc sweep ────────────────────────────────────────────────
        sweep_angle = (t * 2.8) % 360
        for i, width in enumerate([6, 4, 2]):
            alpha = 0.6 - i * 0.15
            col   = self._blend(pri, "#080c14", 1 - alpha)
            c.create_arc(CX-90, CY-90, CX+90, CY+90,
                         start=sweep_angle, extent=70 - i*12,
                         outline=col, width=width, style=tk.ARC)

        # ── Scanning line ────────────────────────────────────────────────────
        self._scan_y = (self._scan_y + 1.8) % 210
        sy = int(CY - 105 + self._scan_y)
        for dy, alpha in [(0, 0.8), (-1, 0.4), (1, 0.4), (-2, 0.15), (2, 0.15)]:
            col = self._blend(pri, "#080c14", 1 - alpha)
            if 0 < sy + dy < SIZE:
                # clip to circle
                rel = abs((sy + dy) - CY)
                if rel < 104:
                    half_w = int(math.sqrt(104**2 - rel**2))
                    c.create_line(CX - half_w, sy + dy,
                                  CX + half_w, sy + dy,
                                  fill=col, width=1)

        # ── Waveform bars (inner ring) ───────────────────────────────────────
        n = len(self._wave_vals)
        for i, v in enumerate(self._wave_vals):
            angle = math.radians(i * 360 / n - 90)
            inner = 42
            outer = inner + int(v * 28)
            x1 = CX + inner * math.cos(angle)
            y1 = CY + inner * math.sin(angle)
            x2 = CX + outer * math.cos(angle)
            y2 = CY + outer * math.sin(angle)
            alpha = 0.4 + v * 0.6
            col   = self._blend(pri, "#ffffff", 1 - alpha * 0.3)
            c.create_line(x1, y1, x2, y2, fill=col, width=2)

        # ── Particles ────────────────────────────────────────────────────────
        for p in self._particles:
            x, y, _, _, life, max_life = p
            alpha = life / max_life
            col   = self._blend(pri, "#080c14", 1 - alpha * 0.9)
            r     = max(1, int(alpha * 2.5))
            c.create_oval(x-r, y-r, x+r, y+r, fill=col, outline="")

        # ── Inner glow core ──────────────────────────────────────────────────
        pulse = 0.85 + 0.15 * math.sin(t * 0.12)
        self._glow_circle(c, CX, CY, int(32 * pulse), pri, layers=4)
        c.create_oval(CX-18, CY-18, CX+18, CY+18,
                      fill="#0d1520", outline=pri, width=1)

        # ── Corner tick marks ────────────────────────────────────────────────
        self._draw_corner_ticks(c, pri)

        # ── Centre text ──────────────────────────────────────────────────────
        c.create_text(CX, CY, text="J.A.R.V.I.S.",
                      fill=pri, font=("Consolas", 7, "bold"))

        # ── State label ──────────────────────────────────────────────────────
        self._label_var.set(cfg["label"])

    # ── Helper shapes ─────────────────────────────────────────────────────────

    def _glow_circle(self, c, cx, cy, r, color, layers=4):
        for i in range(layers, 0, -1):
            rr    = r + i * 5
            alpha = 0.06 * i
            col   = self._blend(color, "#0a0a0a", 1 - alpha)
            c.create_oval(cx-rr, cy-rr, cx+rr, cy+rr, fill=col, outline="")

    def _draw_segmented_ring(self, c, cx, cy, r_out, r_in,
                              segments, gap, angle_offset,
                              color, bright_every=None):
        seg_deg = 360 / segments
        for i in range(segments):
            start = i * seg_deg + angle_offset
            extent = seg_deg - gap
            if bright_every and i % bright_every == 0:
                col = self._blend(color, "#ffffff", 0.6)
                w   = 2
            else:
                col = color
                w   = 1
            c.create_arc(cx-r_out, cy-r_out, cx+r_out, cy+r_out,
                         start=start, extent=extent,
                         outline=col, width=w, style=tk.ARC)

    def _draw_corner_ticks(self, c, color):
        r   = 105
        dim = self._blend(color, "#0a0a0a", 0.5)
        for angle_deg in [45, 135, 225, 315]:
            a   = math.radians(angle_deg)
            ox  = CX + r * math.cos(a)
            oy  = CY + r * math.sin(a)
            # two short perpendicular lines forming an 'L'
            perp = math.radians(angle_deg + 90)
            for sign in (1, -1):
                ex = ox + sign * 8 * math.cos(perp)
                ey = oy + sign * 8 * math.sin(perp)
                c.create_line(ox, oy, ex, ey, fill=dim, width=2)

    @staticmethod
    def _blend(hex_a: str, hex_b: str, t: float) -> str:
        def parse(h):
            h = h.lstrip("#")
            return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        r1,g1,b1 = parse(hex_a)
        r2,g2,b2 = parse(hex_b)
        t = max(0.0, min(1.0, t))
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"

    def _show(self):
        if self._root:
            self._root.after(0, self._root.deiconify)

    def _schedule_hide(self):
        pass  # always visible
