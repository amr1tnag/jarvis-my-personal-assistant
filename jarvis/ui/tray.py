import threading
from PIL import Image, ImageDraw
import pystray


_STATES = {
    "idle": {
        "outer": (30, 60, 120),
        "middle": (50, 100, 180),
        "center": (80, 160, 220),
    },
    "listening": {
        "outer": (0, 180, 220),
        "middle": (0, 220, 255),
        "center": (150, 245, 255),
    },
    "thinking": {
        "outer": (160, 80, 0),
        "middle": (220, 130, 0),
        "center": (255, 200, 50),
    },
}


def _draw_icon(state: str) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    colors = _STATES.get(state, _STATES["idle"])

    cx, cy = size // 2, size // 2

    # Outer ring: filled circle then black hole to make ring
    r_outer = 30
    draw.ellipse(
        [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
        fill=colors["outer"],
    )
    r_outer_inner = 24
    draw.ellipse(
        [cx - r_outer_inner, cy - r_outer_inner, cx + r_outer_inner, cy + r_outer_inner],
        fill=(0, 0, 0, 255),
    )

    # Middle ring
    r_mid = 20
    draw.ellipse(
        [cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid],
        fill=colors["middle"],
    )
    r_mid_inner = 13
    draw.ellipse(
        [cx - r_mid_inner, cy - r_mid_inner, cx + r_mid_inner, cy + r_mid_inner],
        fill=(0, 0, 0, 255),
    )

    # Center filled circle
    r_center = 9
    draw.ellipse(
        [cx - r_center, cy - r_center, cx + r_center, cy + r_center],
        fill=colors["center"],
    )

    return img


def _notify(title: str, message: str, icon: pystray.Icon):
    try:
        icon.notify(message, title)
    except Exception:
        pass


class TrayIcon:
    def __init__(self, on_start_listening=None, on_stop_listening=None, on_exit=None):
        self._listening = False
        self._on_start_listening = on_start_listening
        self._on_stop_listening = on_stop_listening
        self._on_exit = on_exit
        self._icon = None

    def _toggle_listening(self, icon, item):
        if self._listening:
            self._listening = False
            if self._on_stop_listening:
                self._on_stop_listening()
        else:
            self._listening = True
            if self._on_start_listening:
                self._on_start_listening()

    def _exit(self, icon, item):
        icon.stop()
        if self._on_exit:
            self._on_exit()

    def _menu_label(self, item):
        return "Stop Listening" if self._listening else "Start Listening"

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(self._menu_label, self._toggle_listening),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Jarvis", self._exit),
        )

    def set_state(self, state: str):
        if self._icon is not None:
            self._icon.icon = _draw_icon(state)

    def notify(self, title: str, message: str):
        if self._icon is not None:
            _notify(title, message, self._icon)

    def run(self):
        self._icon = pystray.Icon(
            name="Jarvis",
            icon=_draw_icon("idle"),
            title="Jarvis AI",
            menu=self._build_menu(),
        )
        self._icon.run()

    def run_detached(self):
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t
