import tkinter as tk
import threading
import math
import time

_STATES = {
    "idle":       {"label": "",               "color": "#1a1a2e", "glow": "#2a2a4e", "ring": "#334477"},
    "listening":  {"label": "Listening...",   "color": "#0d1b2a", "glow": "#00aaff", "ring": "#00ccff"},
    "thinking":   {"label": "Thinking...",    "color": "#1a0d2e", "glow": "#aa00ff", "ring": "#cc44ff"},
    "speaking":   {"label": "Speaking...",    "color": "#0d2a1a", "glow": "#00ffaa", "ring": "#00ffcc"},
}

SIZE = 200        # canvas size
CX = SIZE // 2    # centre x
CY = SIZE // 2    # centre y
R_OUTER = 88      # outer ring radius
R_INNER = 60      # inner circle radius
R_CORE  = 38      # core glow radius


class JarvisOverlay:
    def __init__(self):
        self._state = "idle"
        self._visible = False
        self._angle = 0.0
        self._pulse = 0.0
        self._running = False
        self._root = None
        self._canvas = None
        self._label_var = None
        self._thread = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def set_state(self, state: str):
        self._state = state if state in _STATES else "idle"
        if state == "idle":
            self._schedule_hide()
        else:
            self._show()

    def start(self):
        """Run the overlay in a dedicated daemon thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _run(self):
        self._root = tk.Tk()
        self._root.overrideredirect(True)           # no title bar
        self._root.attributes("-topmost", True)     # always on top
        self._root.attributes("-transparentcolor", "#000001")
        self._root.configure(bg="#000001")
        self._root.withdraw()                       # start hidden

        # Position: bottom-right corner
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        margin = 20
        x = sw - SIZE - margin
        y = sh - SIZE - 60 - margin
        self._root.geometry(f"{SIZE}x{SIZE+40}+{x}+{y}")

        self._canvas = tk.Canvas(
            self._root, width=SIZE, height=SIZE,
            bg="#000001", highlightthickness=0,
        )
        self._canvas.pack()

        self._label_var = tk.StringVar(value="")
        tk.Label(
            self._root, textvariable=self._label_var,
            bg="#000001", fg="#ccddff",
            font=("Segoe UI", 9, "bold"),
        ).pack()

        self._animate()
        self._root.mainloop()

    def _animate(self):
        if not self._running:
            return
        try:
            self._draw_frame()
        except Exception:
            pass
        self._root.after(33, self._animate)   # ~30 fps

    def _draw_frame(self):
        c = self._canvas
        c.delete("all")

        cfg = _STATES[self._state]
        self._angle = (self._angle + 2.5) % 360
        self._pulse = (self._pulse + 0.06) % (2 * math.pi)
        pulse_scale = 1.0 + 0.08 * math.sin(self._pulse)

        # Outer glow rings (layered transparency illusion)
        for i, alpha in enumerate([0.08, 0.15, 0.25]):
            r = int((R_OUTER + 14 - i * 5) * pulse_scale)
            col = self._blend(cfg["glow"], "#000001", alpha + 0.05)
            c.create_oval(CX - r, CY - r, CX + r, CY + r,
                          fill=col, outline="")

        # Spinning arc segments
        for seg in range(8):
            start = self._angle + seg * 45
            brightness = 0.4 + 0.6 * ((seg % 3) / 2)
            col = self._blend(cfg["ring"], "#000001", brightness)
            c.create_arc(
                CX - R_OUTER, CY - R_OUTER,
                CX + R_OUTER, CY + R_OUTER,
                start=start, extent=28,
                outline=col, width=2, style=tk.ARC,
            )

        # Counter-rotating inner arc
        for seg in range(6):
            start = -self._angle * 1.5 + seg * 60
            col = self._blend(cfg["glow"], "#ffffff", 0.5)
            c.create_arc(
                CX - R_INNER, CY - R_INNER,
                CX + R_INNER, CY + R_INNER,
                start=start, extent=18,
                outline=col, width=1, style=tk.ARC,
            )

        # Core circle
        r_core = int(R_CORE * pulse_scale)
        c.create_oval(
            CX - r_core, CY - r_core,
            CX + r_core, CY + r_core,
            fill=cfg["color"], outline=cfg["glow"], width=2,
        )

        # J.A.R.V.I.S. text
        c.create_text(
            CX, CY, text="J.A.R.V.I.S.",
            fill=cfg["glow"], font=("Segoe UI", 9, "bold"),
        )

        # Tick marks around outer ring
        for i in range(24):
            a = math.radians(i * 15)
            inner_r = R_OUTER - 6
            outer_r = R_OUTER + (6 if i % 6 == 0 else 3)
            x1 = CX + inner_r * math.cos(a)
            y1 = CY - inner_r * math.sin(a)
            x2 = CX + outer_r * math.cos(a)
            y2 = CY - outer_r * math.sin(a)
            col = cfg["glow"] if i % 6 == 0 else cfg["ring"]
            c.create_line(x1, y1, x2, y2, fill=col, width=1)

        self._label_var.set(cfg["label"])

    @staticmethod
    def _blend(hex_a: str, hex_b: str, t: float) -> str:
        """Blend two hex colours. t=0 → hex_a, t=1 → hex_b."""
        def parse(h):
            h = h.lstrip("#")
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r1, g1, b1 = parse(hex_a)
        r2, g2, b2 = parse(hex_b)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _show(self):
        if self._root:
            self._root.after(0, self._root.deiconify)
        self._visible = True
        self._hide_timer = None

    def _schedule_hide(self):
        if self._root:
            self._root.after(1500, self._root.withdraw)
        self._visible = False
