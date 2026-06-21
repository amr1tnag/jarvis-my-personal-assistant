import tkinter as tk
import threading
import math

_STATES = {
    "idle":      {"color": "#1a6aff", "label": "STANDBY"},
    "listening": {"color": "#00d4ff", "label": "LISTENING"},
    "thinking":  {"color": "#aa44ff", "label": "PROCESSING"},
    "speaking":  {"color": "#00ffaa", "label": "SPEAKING"},
}

SIZE = 200
CX   = SIZE // 2
CY   = SIZE // 2


class JarvisOverlay:
    def __init__(self):
        self._state   = "idle"
        self._running = False
        self._root    = None
        self._canvas  = None
        self._lbl_var = None
        self._thread  = None
        self._tick    = 0
        self._spin    = 0.0
        self._pulse   = 0.0

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

    def _run(self):
        try:
            self._root = tk.Tk()
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)
            self._root.configure(bg="#0b0d14")

            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            m  = 16
            x  = sw - SIZE - m
            y  = sh - SIZE - 56 - m
            self._root.geometry(f"{SIZE}x{SIZE+18}+{x}+{y}")
            print(f"[Overlay] starting at ({x},{y})")

            self._canvas = tk.Canvas(
                self._root, width=SIZE, height=SIZE,
                bg="#0b0d14", highlightthickness=0,
            )
            self._canvas.pack()

            self._lbl_var = tk.StringVar(value="")
            tk.Label(
                self._root, textvariable=self._lbl_var,
                bg="#0b0d14", fg="#334466",
                font=("Consolas", 7),
            ).pack()

            self._root.deiconify()
            self._loop()
            self._root.mainloop()
        except Exception as e:
            print(f"[Overlay] FATAL: {e}")

    def _loop(self):
        if not self._running:
            return
        try:
            self._tick  += 1
            self._spin   = (self._spin + 1.2) % 360
            self._pulse  = (self._pulse + 0.07) % (2 * math.pi)
            self._draw()
        except Exception as e:
            print(f"[Overlay] draw error: {e}")
        self._root.after(30, self._loop)

    def _draw(self):
        c   = self._canvas
        cfg = _STATES[self._state]
        col = cfg["color"]
        bg  = "#0b0d14"

        c.delete("all")

        p = math.sin(self._pulse)   # -1 … +1

        # ── Outer faint ring ─────────────────────────────────────────────────
        dim = self._blend(col, bg, 0.82)
        c.create_oval(CX-88, CY-88, CX+88, CY+88,
                      outline=dim, width=1)

        # ── Rotating dashed arc (outer) ──────────────────────────────────────
        for i in range(12):
            a = self._spin + i * 30
            c.create_arc(CX-88, CY-88, CX+88, CY+88,
                         start=a, extent=18,
                         outline=col, width=1, style=tk.ARC)

        # ── Counter-rotating inner arc ────────────────────────────────────────
        inner_col = self._blend(col, "#ffffff", 0.35)
        for i in range(6):
            a = -self._spin * 1.6 + i * 60
            c.create_arc(CX-66, CY-66, CX+66, CY+66,
                         start=a, extent=24,
                         outline=inner_col, width=1, style=tk.ARC)

        # ── Pulsing glow rings ────────────────────────────────────────────────
        for r_add, alpha in [(10, 0.08), (6, 0.14), (3, 0.22), (0, 0.40)]:
            r   = int(44 + r_add + 4 * p)
            clr = self._blend(col, bg, 1 - alpha)
            c.create_oval(CX-r, CY-r, CX+r, CY+r, fill=clr, outline="")

        # ── Core circle ───────────────────────────────────────────────────────
        c.create_oval(CX-26, CY-26, CX+26, CY+26,
                      fill="#0e1220", outline=col, width=1)

        # ── J.A.R.V.I.S. text ────────────────────────────────────────────────
        c.create_text(CX, CY, text="J.A.R.V.I.S.",
                      fill=col, font=("Consolas", 7, "bold"))

        # ── Four tick marks at cardinal points ────────────────────────────────
        for angle_deg in [0, 90, 180, 270]:
            a  = math.radians(angle_deg + self._spin * 0.3)
            r1, r2 = 88, 96
            x1 = CX + r1 * math.cos(a)
            y1 = CY + r1 * math.sin(a)
            x2 = CX + r2 * math.cos(a)
            y2 = CY + r2 * math.sin(a)
            c.create_line(x1, y1, x2, y2, fill=col, width=2)

        self._lbl_var.set(cfg["label"])

    @staticmethod
    def _blend(hex_a: str, hex_b: str, t: float) -> str:
        def p(h):
            h = h.lstrip("#")
            return int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
        r1, g1, b1 = p(hex_a)
        r2, g2, b2 = p(hex_b)
        t = max(0.0, min(1.0, t))
        return (f"#{int(r1+(r2-r1)*t):02x}"
                f"{int(g1+(g2-g1)*t):02x}"
                f"{int(b1+(b2-b1)*t):02x}")
