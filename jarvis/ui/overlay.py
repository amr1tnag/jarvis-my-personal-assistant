import tkinter as tk
import threading
import math
import time
import random

_STATES = {
    "idle":      {"color": "#0099dd", "bright": "#33ccff", "dim": "#003355", "label": "STANDBY"},
    "listening": {"color": "#00ccff", "bright": "#ffffff", "dim": "#004466", "label": "LISTENING"},
    "thinking":  {"color": "#9933ff", "bright": "#cc88ff", "dim": "#330055", "label": "PROCESSING"},
    "speaking":  {"color": "#00ffaa", "bright": "#aaffdd", "dim": "#004433", "label": "SPEAKING"},
}

SIZE = 320
CX   = SIZE // 2
CY   = SIZE // 2


class JarvisOverlay:
    def __init__(self):
        self._state    = "idle"
        self._running  = False
        self._root     = None
        self._canvas   = None
        self._lbl_var  = None
        self._thread   = None
        self._tick     = 0
        self._ring1    = 0.0    # outer ring rotation
        self._ring2    = 0.0    # mid ring rotation (opposite)
        self._ring3    = 0.0    # inner dash ring
        self._scan     = 0.0    # scanner angle
        self._wave     = [0.0] * 20
        self._data_tick = 0

    def set_state(self, state: str):
        self._state = state if state in _STATES else "idle"
        if self._root:
            self._root.after(0, self._root.deiconify)

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

    def _schedule_hide(self):
        pass

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self):
        try:
            self._root = tk.Tk()
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)
            self._root.configure(bg="#0a0a12")

            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            m  = 16
            x  = sw - SIZE - m
            y  = sh - SIZE - 60 - m
            self._root.geometry(f"{SIZE}x{SIZE+20}+{x}+{y}")
            print(f"[Overlay] starting at ({x},{y})")

            self._canvas = tk.Canvas(self._root, width=SIZE, height=SIZE,
                                     bg="#0a0a12", highlightthickness=0)
            self._canvas.pack()

            self._lbl_var = tk.StringVar(value="")
            tk.Label(self._root, textvariable=self._lbl_var,
                     bg="#0a0a12", fg="#0099cc",
                     font=("Consolas", 8, "bold")).pack()

            self._root.deiconify()
            self._loop()
            self._root.mainloop()
        except Exception as e:
            print(f"[Overlay] FATAL: {e}")

    def _loop(self):
        if not self._running:
            return
        try:
            self._tick      += 1
            self._ring1      = (self._ring1 + 0.4)  % 360
            self._ring2      = (self._ring2 - 0.7)  % 360
            self._ring3      = (self._ring3 + 1.1)  % 360
            self._scan       = (self._scan  + 2.2)  % 360
            self._data_tick  = (self._data_tick + 1) % 60
            self._update_wave()
            self._draw()
        except Exception as e:
            print(f"[Overlay] draw error: {e}")
        self._root.after(28, self._loop)

    def _update_wave(self):
        s = self._state
        for i in range(len(self._wave)):
            if s == "listening":
                t = random.uniform(0.15, 1.0)
            elif s == "speaking":
                t = abs(math.sin(self._tick * 0.15 + i * 0.6)) * 0.85 + 0.1
            elif s == "thinking":
                t = 0.3 + 0.25 * math.sin(self._tick * 0.07 + i * 0.9)
            else:
                t = 0.06 + 0.04 * math.sin(self._tick * 0.03 + i)
            self._wave[i] += (t - self._wave[i]) * 0.2

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw(self):
        c   = self._canvas
        cfg = _STATES[self._state]
        col = cfg["color"]
        brt = cfg["bright"]
        dim = cfg["dim"]
        t   = self._tick

        c.delete("all")

        # ── 1. Dark base plate ────────────────────────────────────────────────
        c.create_oval(CX-148, CY-148, CX+148, CY+148,
                      fill="#0a0a12", outline=dim, width=1)

        # ── 2. Outermost ring: 90 tick marks ─────────────────────────────────
        for i in range(90):
            a     = math.radians(i * 4 + self._ring1)
            major = (i % 5 == 0)
            r_in  = 140 if major else 143
            r_out = 148
            x1    = CX + r_in  * math.cos(a)
            y1    = CY + r_in  * math.sin(a)
            x2    = CX + r_out * math.cos(a)
            y2    = CY + r_out * math.sin(a)
            clr   = brt if major else col
            w     = 2  if major else 1
            c.create_line(x1, y1, x2, y2, fill=clr, width=w)

        # ── 3. Second ring: 24 segments ───────────────────────────────────────
        for i in range(24):
            a_start = i * 15 + self._ring1 * 0.5
            a_end   = a_start + 11
            bright  = (i % 6 == 0)
            clr     = brt if bright else col
            w       = 2   if bright else 1
            c.create_arc(CX-128, CY-128, CX+128, CY+128,
                         start=a_start, extent=11,
                         outline=clr, width=w, style=tk.ARC)

        # ── 4. Third ring (opposite spin): fine dashes ────────────────────────
        for i in range(48):
            a     = math.radians(i * 7.5 + self._ring2)
            r     = 114
            dr    = 6 if i % 4 == 0 else 3
            x1    = CX + r        * math.cos(a)
            y1    = CY + r        * math.sin(a)
            x2    = CX + (r - dr) * math.cos(a)
            y2    = CY + (r - dr) * math.sin(a)
            c.create_line(x1, y1, x2, y2, fill=dim, width=1)

        # ── 5. Scanner beam ───────────────────────────────────────────────────
        scan_rad = math.radians(self._scan)
        for layer, (r_out, r_in, alpha) in enumerate([
                (108, 60, 0.9), (108, 60, 0.5), (108, 60, 0.25)]):
            spread = layer * 6
            for ds in range(-spread, spread + 1, max(1, spread)):
                a   = scan_rad + math.radians(ds)
                clr = self._blend(col, "#0a0a12", 1 - alpha / (abs(ds)+1))
                x1  = CX + r_in  * math.cos(a)
                y1  = CY + r_in  * math.sin(a)
                x2  = CX + r_out * math.cos(a)
                y2  = CY + r_out * math.sin(a)
                c.create_line(x1, y1, x2, y2, fill=clr, width=1)

        # ── 6. Main glowing arc ring ──────────────────────────────────────────
        pulse   = 0.88 + 0.12 * math.sin(t * 0.1)
        arc_r   = int(104 * pulse)
        # Glow layers
        for width, blend_t in [(8, 0.85), (5, 0.6), (3, 0.35), (1, 0.0)]:
            clr = self._blend(col, "#0a0a12", blend_t)
            c.create_oval(CX-arc_r, CY-arc_r, CX+arc_r, CY+arc_r,
                          outline=clr, width=width)
        # Bright highlight arc
        c.create_arc(CX-arc_r, CY-arc_r, CX+arc_r, CY+arc_r,
                     start=self._ring3, extent=120,
                     outline=brt, width=2, style=tk.ARC)
        c.create_arc(CX-arc_r, CY-arc_r, CX+arc_r, CY+arc_r,
                     start=self._ring3 + 180, extent=60,
                     outline=brt, width=1, style=tk.ARC)

        # ── 7. Inner segmented ring ───────────────────────────────────────────
        for i in range(36):
            a_start = i * 10 - self._ring1 * 0.8
            c.create_arc(CX-82, CY-82, CX+82, CY+82,
                         start=a_start, extent=7,
                         outline=dim, width=1, style=tk.ARC)

        # ── 8. Waveform bars ──────────────────────────────────────────────────
        n = len(self._wave)
        for i, v in enumerate(self._wave):
            a      = math.radians(i * (360 / n) - 90)
            r_base = 54
            r_tip  = r_base + int(v * 18)
            x1 = CX + r_base * math.cos(a)
            y1 = CY + r_base * math.sin(a)
            x2 = CX + r_tip  * math.cos(a)
            y2 = CY + r_tip  * math.sin(a)
            clr = brt if v > 0.7 else col
            c.create_line(x1, y1, x2, y2, fill=clr, width=1)

        # ── 9. Core: dark circle + cross-hairs + J.A.R.V.I.S. text ──────────
        c.create_oval(CX-46, CY-46, CX+46, CY+46,
                      fill="#0a0a12", outline=col, width=1)
        # crosshair lines
        for angle in [0, 90]:
            a = math.radians(angle)
            c.create_line(CX - 42*math.cos(a), CY - 42*math.sin(a),
                          CX + 42*math.cos(a), CY + 42*math.sin(a),
                          fill=dim, width=1)
        # Small inner ring
        c.create_oval(CX-28, CY-28, CX+28, CY+28,
                      outline=col, width=1)
        # Text
        c.create_text(CX, CY, text="J.A.R.V.I.S.",
                      fill=brt, font=("Consolas", 7, "bold"))

        # ── 10. Cardinal data labels ──────────────────────────────────────────
        flip = (self._data_tick % 60 < 2)   # flash occasionally
        labels = {
            90:  f"{random.randint(98,100) if flip else 99}%",
            270: f"{random.randint(11,13) if flip else 12}ms",
            0:   "SYS",
            180: "NET",
        }
        for angle_deg, txt in labels.items():
            a   = math.radians(angle_deg)
            r   = 136
            x   = CX + r * math.cos(a)
            y   = CY + r * math.sin(a)
            c.create_text(x, y, text=txt, fill=dim,
                          font=("Consolas", 6, "bold"))

        # ── 11. Corner bracket marks ──────────────────────────────────────────
        for ang in [45, 135, 225, 315]:
            a  = math.radians(ang)
            ox = CX + 148 * math.cos(a)
            oy = CY + 148 * math.sin(a)
            pa = math.radians(ang + 90)
            for sign in (1, -1):
                ex = ox + sign * 7 * math.cos(pa)
                ey = oy + sign * 7 * math.sin(pa)
                c.create_line(ox, oy, ex, ey, fill=col, width=1)

        self._lbl_var.set(cfg["label"])

    @staticmethod
    def _blend(hex_a: str, hex_b: str, t: float) -> str:
        def p(h):
            h = h.lstrip("#")
            return int(h[:2],16), int(h[2:4],16), int(h[4:],16)
        r1,g1,b1 = p(hex_a)
        r2,g2,b2 = p(hex_b)
        t = max(0.0, min(1.0, t))
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"
