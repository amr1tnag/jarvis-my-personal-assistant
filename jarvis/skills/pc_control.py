import os
import subprocess
import webbrowser
import glob
import time
from datetime import datetime

import os as _os

def _p(*parts):
    p = _os.path.join(*parts)
    return p if _os.path.exists(p) else None

def _find_exe(folder: str, name: str) -> str | None:
    """Glob-search for an exe under a folder (handles versioned subdirs)."""
    pattern = _os.path.join(folder, "**", name)
    matches = glob.glob(pattern, recursive=True)
    return matches[0] if matches else None

_LOCAL = _os.environ.get("LOCALAPPDATA", "")
_PROG  = _os.environ.get("PROGRAMFILES", "C:\\Program Files")
_PROG86= _os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
_USER  = _os.environ.get("USERPROFILE", "C:\\Users\\Amrit")

APP_MAP = {
    "vs code":            _p(_LOCAL, "Programs", "Microsoft VS Code", "Code.exe") or "code",
    "vscode":             _p(_LOCAL, "Programs", "Microsoft VS Code", "Code.exe") or "code",
    "visual studio code": _p(_LOCAL, "Programs", "Microsoft VS Code", "Code.exe") or "code",
    "chrome":             (_p(_PROG,   "Google", "Chrome", "Application", "chrome.exe") or
                           _p(_PROG86, "Google", "Chrome", "Application", "chrome.exe") or
                           _p(_LOCAL,  "Google", "Chrome", "Application", "chrome.exe") or "chrome"),
    "google chrome":      (_p(_PROG,   "Google", "Chrome", "Application", "chrome.exe") or
                           _p(_LOCAL,  "Google", "Chrome", "Application", "chrome.exe") or "chrome"),
    "spotify":            (_p(_LOCAL, "Microsoft", "WindowsApps", "Spotify.exe") or
                           _p(_USER,  "AppData", "Roaming", "Spotify", "Spotify.exe") or
                           "spotify:"),
    "discord":            (_find_exe(_os.path.join(_LOCAL, "Discord"), "Discord.exe") or "discord"),
    "file explorer":      "explorer",
    "notepad":            "notepad",
    "calculator":         "calc",
    "calc":               "calc",
    "word":               _p(_PROG, "Microsoft Office", "root", "Office16", "WINWORD.EXE")  or "winword",
    "microsoft word":     _p(_PROG, "Microsoft Office", "root", "Office16", "WINWORD.EXE")  or "winword",
    "excel":              _p(_PROG, "Microsoft Office", "root", "Office16", "EXCEL.EXE")    or "excel",
    "powerpoint":         _p(_PROG, "Microsoft Office", "root", "Office16", "POWERPNT.EXE") or "powerpnt",
    # WhatsApp — try exe first, then URI scheme, then Store shell path
    "whatsapp":           (_p(_LOCAL, "WhatsApp", "WhatsApp.exe") or "whatsapp:"),
    "telegram":           (_p(_PROG, "Telegram Desktop", "Telegram.exe") or
                           _p(_USER, "AppData", "Roaming", "Telegram Desktop", "Telegram.exe") or "telegram"),
    "vlc":                (_p(_PROG,   "VideoLAN", "VLC", "vlc.exe") or
                           _p(_PROG86, "VideoLAN", "VLC", "vlc.exe") or "vlc"),
    "task manager":       "taskmgr",
    "settings":           "ms-settings:",
    "paint":              "mspaint",
    "cmd":                "cmd",
    "command prompt":     "cmd",
    "powershell":         "powershell",
    "terminal":           "wt",
    "windows terminal":   "wt",
    "edge":               (_p(_PROG, "Microsoft", "Edge", "Application", "msedge.exe") or "msedge"),
    "microsoft edge":     (_p(_PROG, "Microsoft", "Edge", "Application", "msedge.exe") or "msedge"),
    "firefox":            (_p(_PROG,   "Mozilla Firefox", "firefox.exe") or
                           _p(_PROG86, "Mozilla Firefox", "firefox.exe") or "firefox"),
    "steam":              (_p(_PROG86, "Steam", "steam.exe") or "steam"),
    "obs":                (_p(_PROG, "obs-studio", "bin", "64bit", "obs64.exe") or "obs64"),
    # Claude desktop — MSIX package (PackageFamilyName: Claude_pzs8sxrjxfjjc)
    "claude":             "shell:AppsFolder\\Claude_pzs8sxrjxfjjc!Claude",
}

PROCESS_MAP = {
    "vs code": "Code.exe", "vscode": "Code.exe", "visual studio code": "Code.exe",
    "chrome": "chrome.exe", "google chrome": "chrome.exe",
    "spotify": "Spotify.exe", "discord": "Discord.exe",
    "file explorer": "explorer.exe",
    "notepad": "notepad.exe", "calculator": "CalculatorApp.exe", "calc": "CalculatorApp.exe",
    "word": "WINWORD.EXE", "microsoft word": "WINWORD.EXE",
    "excel": "EXCEL.EXE", "powerpoint": "POWERPNT.EXE",
    "whatsapp": "WhatsApp.exe", "telegram": "Telegram.exe", "vlc": "vlc.exe",
    "task manager": "Taskmgr.exe",
    "edge": "msedge.exe", "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe", "steam": "steam.exe", "obs": "obs64.exe",
    "paint": "mspaint.exe", "cmd": "cmd.exe", "powershell": "powershell.exe",
    "claude": "claude.exe",
}

# Words too generic to fuzzy-match — must be an exact APP_MAP key
_NO_FUZZY = {"files", "explorer", "app", "application", "program", "browser", "open"}

def _fuzzy_match_app(key: str) -> str | None:
    if key in _NO_FUZZY:
        return None
    if key in APP_MAP:
        return key
    # substring match
    for k in APP_MAP:
        if k in key or key in k:
            return k
    # word overlap — require at least 2 matching words to avoid false positives
    key_words = set(key.split())
    best, best_score = None, 0
    for k in APP_MAP:
        score = len(key_words & set(k.split()))
        if score > best_score:
            best, best_score = k, score
    return best if best_score >= 2 else None


def open_application(name: str) -> str:
    key = name.lower().strip()
    matched = _fuzzy_match_app(key)
    exe = APP_MAP.get(matched, key) if matched else key

    # Any URI scheme (whatsapp:, claude:, spotify:, shell:, ms-settings:, etc.)
    if ":" in exe and exe[1] != ":":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", exe],
                             creationflags=subprocess.DETACHED_PROCESS,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening {name}, sir."
        except Exception as e:
            return f"Couldn't open {name}, sir. {e}"

    # Extra args for specific apps (e.g. Chrome needs profile flag to open signed-in account)
    EXTRA_ARGS: dict[str, list[str]] = {
        "chrome": ["--profile-directory=Default"],
        "google chrome": ["--profile-directory=Default"],
    }
    extra = EXTRA_ARGS.get(matched or key, [])

    # If it's a full path that exists, launch with subprocess so we can pass extra args
    if os.path.isfile(exe):
        try:
            subprocess.Popen([exe] + extra, creationflags=subprocess.DETACHED_PROCESS)
            return f"Opening {name}, sir."
        except Exception as e:
            return f"Couldn't open {name}, sir. {e}"

    # Fall back to shell command (for things like notepad, calc, explorer in PATH)
    try:
        cmd = exe + (" " + " ".join(extra) if extra else "")
        subprocess.Popen(cmd, shell=True, creationflags=subprocess.DETACHED_PROCESS)
        return f"Opening {name}, sir."
    except Exception as e:
        return f"Couldn't open '{name}', sir. It may not be installed. {e}"


def close_application(name: str) -> str:
    key = name.lower().strip()
    matched = _fuzzy_match_app(key)
    process = PROCESS_MAP.get(matched or key, key if key.endswith(".exe") else key + ".exe")

    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", process],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return f"Closed {name}."
        return f"Could not close '{name}': {result.stderr.strip()}"
    except Exception as e:
        return f"Failed to close '{name}': {e}"


def search_files(query: str, location: str = None) -> str:
    if location:
        search_dirs = [location]
    else:
        base = os.path.expanduser("~")
        search_dirs = [
            os.path.join(base, "Documents"),
            os.path.join(base, "Downloads"),
            os.path.join(base, "Desktop"),
            base,
        ]

    matches = []
    query_lower = query.lower()

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in files:
                if query_lower in filename.lower():
                    matches.append(os.path.join(root, filename))
                if len(matches) >= 10:
                    break
            if len(matches) >= 10:
                break

    if not matches:
        return f"No files found matching '{query}'."
    return "Found files:\n" + "\n".join(matches[:10])


def get_running_apps() -> str:
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        )
        lines = result.stdout.strip().splitlines()
        seen = set()
        names = []
        for line in lines:
            parts = line.split(",")
            if parts:
                proc = parts[0].strip('"')
                base = os.path.splitext(proc)[0]
                if base.lower() not in seen:
                    seen.add(base.lower())
                    names.append(base)
        names.sort(key=str.lower)
        return "Running processes:\n" + ", ".join(names)
    except Exception as e:
        return f"Failed to get running apps: {e}"


def set_volume(level: int) -> str:
    level = max(0, min(100, level))

    # Try pycaw first (fastest, no subprocess)
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(interface, POINTER(IAudioEndpointVolume))
        vol.SetMasterVolumeLevelScalar(level / 100, None)
        return f"Volume set to {level}%, sir."
    except Exception:
        pass

    # Fallback: nircmd (if installed) — single clean call
    try:
        subprocess.run(
            ["nircmd", "setsysvolume", str(int(level / 100 * 65535))],
            capture_output=True, timeout=5,
        )
        return f"Volume set to {level}%, sir."
    except Exception:
        pass

    # Final fallback: PowerShell with Windows.Audio WinRT API
    script = (
        f"$vol = {level / 100};"
        "[void][Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType=WindowsRuntime] 2>$null;"
        "Add-Type -AssemblyName System.Runtime.InteropServices;"
        "try {"
        "  $t = [Type]::GetTypeFromCLSID([Guid]'BCDE0395-E52F-467C-8E3D-C4579291692E');"
        "  $d = [Activator]::CreateInstance($t);"
        "  $ep = $d.GetType().GetMethod('GetDefaultAudioEndpoint').Invoke($d,@(0,1));"
        "  $v  = $ep.GetType().GetMethod('Activate').Invoke($ep,@([Guid]'5CDF2C82-841E-4546-9722-0CF74078229A',23,0));"
        f" $v.GetType().GetMethod('SetMasterVolumeLevelScalar').Invoke($v,@([float]{level/100},[Guid]::Empty));"
        "} catch {}"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True, timeout=10)
        return f"Volume set to {level}%, sir."
    except Exception as e:
        return f"Couldn't set volume: {e}"


def take_screenshot(filename: str = None) -> str:
    try:
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
        except ImportError:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = os.path.join(desktop, f"screenshot_{timestamp}.png")

        screenshot.save(filename)
        return f"Screenshot saved to {filename}"
    except Exception as e:
        return f"Failed to take screenshot: {e}"


def type_text(text: str) -> str:
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=0.02)
        return f"Typed: {text}"
    except ImportError:
        return "pyautogui is not installed. Run: pip install pyautogui"
    except Exception as e:
        return f"Failed to type text: {e}"


def press_key(key: str) -> str:
    try:
        import pyautogui
        key = key.lower().replace(" ", "")
        if "+" in key:
            parts = key.split("+")
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(key)
        return f"Pressed key: {key}"
    except ImportError:
        return "pyautogui is not installed. Run: pip install pyautogui"
    except Exception as e:
        return f"Failed to press key '{key}': {e}"


def open_url(url: str) -> str:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened URL: {url}"
    except Exception as e:
        return f"Failed to open URL '{url}': {e}"


def shutdown_pc(action: str = "shutdown") -> str:
    action = action.lower().strip()
    if action in ("shutdown", "shut down", "turn off", "power off"):
        return (
            "This will shut down your PC in 5 seconds. "
            "Say 'confirm shutdown' to proceed, or 'cancel shutdown' to abort."
            " [PENDING: shutdown /s /t 5]"
        )
    elif action in ("restart", "reboot"):
        return (
            "This will restart your PC in 5 seconds. "
            "Say 'confirm restart' to proceed, or 'cancel restart' to abort."
            " [PENDING: shutdown /r /t 5]"
        )
    elif action in ("sleep", "hibernate"):
        return (
            "This will put your PC to sleep. "
            "Say 'confirm sleep' to proceed."
            " [PENDING: rundll32.exe powrprof.dll,SetSuspendState 0,1,0]"
        )
    elif action.startswith("confirm"):
        sub_action = action.replace("confirm", "").strip()
        if sub_action in ("shutdown", "shut down", "turn off", "power off"):
            subprocess.Popen(["shutdown", "/s", "/t", "5"])
            return "Shutting down in 5 seconds, sir."
        elif sub_action in ("restart", "reboot"):
            subprocess.Popen(["shutdown", "/r", "/t", "5"])
            return "Restarting in 5 seconds, sir."
        elif sub_action in ("sleep",):
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return "Going to sleep, sir."
        return f"Unrecognised confirm action: '{sub_action}'"
    elif action == "cancel":
        subprocess.run(["shutdown", "/a"], capture_output=True)
        return "Shutdown/restart cancelled."
    else:
        return (
            f"Unknown power action '{action}'. "
            "Valid options: shutdown, restart, sleep, confirm shutdown, confirm restart, confirm sleep, cancel."
        )


def _get_monitors():
    """Return (external, laptop) monitor info sorted by x position (external is leftmost)."""
    try:
        from screeninfo import get_monitors
        monitors = sorted(get_monitors(), key=lambda m: m.x)
        for i, m in enumerate(monitors):
            print(f"[Monitor {i}] x={m.x} y={m.y} {m.width}x{m.height}")
        if len(monitors) >= 2:
            return monitors[0], monitors[1]   # external=left, laptop=right
        return monitors[0], monitors[0]
    except Exception:
        class _M:
            def __init__(self, x, y, w, h):
                self.x, self.y, self.width, self.height = x, y, w, h
        return _M(0, 0, 1920, 1080), _M(1920, 0, 1920, 1080)


def _move_window(title_substr: str, x: int, y: int, w: int, h: int,
                 retries: int = 30, fullscreen: bool = False):
    """Find a window and move/resize it using Win32 SetWindowPos."""
    import ctypes
    user32 = ctypes.windll.user32

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

    SW_RESTORE     = 9
    SW_MAXIMIZE    = 3
    SWP_SHOWWINDOW = 0x0040
    SWP_NOZORDER   = 0x0004
    SWP_FRAMECHANGED = 0x0020

    for attempt in range(retries):
        try:
            import pygetwindow as gw
            matches = [win for win in gw.getAllWindows()
                       if title_substr.lower() in win.title.lower() and win.title.strip()]
            if matches:
                hwnd = matches[0]._hWnd
                # Unmaximize first, wait for it to settle
                user32.ShowWindow(hwnd, SW_RESTORE)
                time.sleep(0.15)
                # Move and resize
                user32.SetWindowPos(hwnd, 0, x, y, w, h,
                                    SWP_SHOWWINDOW | SWP_NOZORDER | SWP_FRAMECHANGED)
                time.sleep(0.1)
                # Verify position stuck; retry if Chrome snapped back
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                if abs(rect.left - x) > 50 or abs(rect.top - y) > 50:
                    time.sleep(0.3)
                    user32.SetWindowPos(hwnd, 0, x, y, w, h,
                                        SWP_SHOWWINDOW | SWP_NOZORDER | SWP_FRAMECHANGED)
                if fullscreen:
                    time.sleep(0.2)
                    user32.ShowWindow(hwnd, SW_MAXIMIZE)
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _get_taskbar_height() -> int:
    """Return taskbar height in pixels using Windows work area."""
    try:
        import ctypes
        class RECT(ctypes.Structure):
            _fields_ = [("left","l","top","l","right","l","bottom","l")]
        # SPI_GETWORKAREA = 48
        rect = ctypes.create_string_buffer(16)
        ctypes.windll.user32.SystemParametersInfoW(48, 0, rect, 0)
        import struct
        l, t, r, b = struct.unpack("llll", rect.raw)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return screen_h - b
    except Exception:
        return 48   # safe default


def work_setup() -> str:
    """
    Set up Amrit's work system:
    - External monitor (left): Chrome (left 60%), Claude (top-right 40%), WhatsApp (bottom-right 40%)
    - Laptop screen (right): dopamine video fullscreen
    - Volume: 100%
    """
    import threading

    set_volume(100)

    ext, lap = _get_monitors()

    def _work_area(mon):
        """Get usable (non-taskbar) area for a monitor via Win32 GetMonitorInfo."""
        try:
            import ctypes, ctypes.wintypes
            # Find the HMONITOR for this monitor by point
            cx = mon.x + mon.width // 2
            cy = mon.y + mon.height // 2
            hmon = ctypes.windll.user32.MonitorFromPoint(
                ctypes.wintypes.POINT(cx, cy), 2)  # MONITOR_DEFAULTTONEAREST

            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                             ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                             ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(info))
            wa = info.rcWork
            return wa.left, wa.top, wa.right - wa.left, wa.bottom - wa.top
        except Exception:
            return mon.x, mon.y, mon.width, mon.height - 48

    ext_x, ext_y, ext_w, ext_h = _work_area(ext)
    lap_x, lap_y, lap_w, lap_h = _work_area(lap)

    print(f"[work_setup] ext work area: {ext_x},{ext_y} {ext_w}x{ext_h}")
    print(f"[work_setup] lap work area: {lap_x},{lap_y} {lap_w}x{lap_h}")

    # ── External monitor layout ──────────────────────────────────────────────
    # Claude: top-left 40%
    claude_x, claude_y = ext_x, ext_y
    claude_w, claude_h = int(ext_w * 0.4), ext_h // 2

    # WhatsApp: bottom-left 40%
    wa_x, wa_y = ext_x, ext_y + ext_h // 2
    wa_w, wa_h = int(ext_w * 0.4), ext_h // 2

    # Chrome: right 60%
    chrome_x, chrome_y = ext_x + int(ext_w * 0.4), ext_y
    chrome_w, chrome_h = int(ext_w * 0.6), ext_h

    # ── Find dopamine video ──────────────────────────────────────────────────
    video_extensions = (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm")
    _hardcoded = os.path.join(os.path.expanduser("~"), "Downloads", "dopamine.mp4")
    dopamine_file = _hardcoded if os.path.exists(_hardcoded) else None

    if not dopamine_file:
        search_dirs = [
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.expanduser("~"), "Videos"),
        ]
        for folder in search_dirs:
            if not os.path.isdir(folder):
                continue
            for f in os.listdir(folder):
                if "dopamine" in f.lower() and f.lower().endswith(video_extensions):
                    dopamine_file = os.path.join(folder, f)
                    break
            if dopamine_file:
                break

    # ── Launch apps ─────────────────────────────────────────────────────────
    # Kill existing Chrome so it opens fresh (position flags ignored if already running)
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(0.8)

    chrome_exe = APP_MAP.get("chrome", "chrome")

    def _launch_chrome():
        try:
            exe = chrome_exe if os.path.isfile(chrome_exe) else "chrome"
            subprocess.Popen(
                [exe, "--profile-directory=Default", "--no-restore-last-session", "--new-window"],
                creationflags=subprocess.DETACHED_PROCESS,
                shell=not os.path.isfile(chrome_exe),
            )
        except Exception:
            open_application("chrome")

    def _launch_claude():
        try:
            subprocess.Popen(["explorer", "shell:AppsFolder\\Claude_pzs8sxrjxfjjc!Claude"])
        except Exception:
            pass

    threading.Thread(target=_launch_chrome, daemon=True).start()
    time.sleep(0.3)
    threading.Thread(target=_launch_claude, daemon=True).start()
    time.sleep(0.3)
    threading.Thread(target=open_application, args=("whatsapp",), daemon=True).start()

    # ── Arrange windows ──────────────────────────────────────────────────────
    import ctypes
    user32 = ctypes.windll.user32
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    SWP_FLAGS = 0x0040 | 0x0004 | 0x0020   # SWP_SHOWWINDOW | SWP_NOZORDER | SWP_FRAMECHANGED

    def _force_window(title_substr: str, x: int, y: int, w: int, h: int,
                      timeout: float = 20.0, interval: float = 0.15):
        """Hammer a window into position every `interval` seconds for `timeout` seconds."""
        import pygetwindow as gw
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                wins = [win for win in gw.getAllWindows()
                        if title_substr.lower() in win.title.lower() and win.title.strip()]
                if wins:
                    hwnd = wins[0]._hWnd
                    user32.ShowWindow(hwnd, 9)   # SW_RESTORE (un-maximize)
                    user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_FLAGS)
            except Exception:
                pass
            time.sleep(interval)

    def _arrange():
        time.sleep(4)   # let apps open before we start moving them
        threading.Thread(target=_force_window,
                         args=("chrome",   chrome_x, chrome_y, chrome_w, chrome_h),
                         kwargs={"timeout": 20}, daemon=True).start()
        threading.Thread(target=_force_window,
                         args=("claude",   claude_x, claude_y, claude_w, claude_h),
                         kwargs={"timeout": 20}, daemon=True).start()
        threading.Thread(target=_force_window,
                         args=("whatsapp", wa_x, wa_y, wa_w, wa_h),
                         kwargs={"timeout": 20}, daemon=True).start()

    threading.Thread(target=_arrange, daemon=True).start()

    # ── Play dopamine video fullscreen ───────────────────────────────────────
    if dopamine_file:
        def _play_video():
            vlc_exe = APP_MAP.get("vlc", "")
            if vlc_exe and os.path.isfile(vlc_exe):
                subprocess.Popen(
                    [vlc_exe, "--fullscreen", "--no-video-title-show", dopamine_file],
                    creationflags=subprocess.DETACHED_PROCESS,
                )
                time.sleep(1)
                set_volume(100)
                return

            os.startfile(dopamine_file)
            time.sleep(4)   # wait for player to fully load
            set_volume(100)

            # Find and fullscreen the media player window
            try:
                import pygetwindow as gw
                import pyautogui
                video_titles = ["media player", "windows media player",
                                "movies & tv", "film & tv", "dopamine", "vlc"]
                for _ in range(20):
                    wins = [w for w in gw.getAllWindows()
                            if any(t in w.title.lower() for t in video_titles)
                            and w.title.strip()]
                    if wins:
                        hwnd = wins[0]._hWnd
                        # Move to full laptop screen first (including taskbar area)
                        user32.SetForegroundWindow(hwnd)
                        time.sleep(0.2)
                        user32.ShowWindow(hwnd, 9)   # SW_RESTORE
                        time.sleep(0.1)
                        user32.SetWindowPos(hwnd, 0,
                                            lap_x, lap_y, lap.width, lap.height,
                                            0x0040 | 0x0004)
                        time.sleep(0.3)
                        # Press F11 to go fullscreen
                        user32.SetForegroundWindow(hwnd)
                        time.sleep(0.1)
                        pyautogui.press("f11")
                        time.sleep(0.3)
                        pyautogui.press("f11")   # second press in case first toggled wrong
                        break
                    time.sleep(0.5)
            except Exception:
                pass

        threading.Thread(target=_play_video, daemon=True).start()

    # ── Arrange windows ──────────────────────────────────────────────────────
    def _move_chrome():
        """Move Chrome and keep hammering for 10s in case it resizes itself."""
        import ctypes
        user32 = ctypes.windll.user32
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
        deadline = time.time() + 10
        hwnd_found = None
        while time.time() < deadline:
            try:
                import pygetwindow as gw
                wins = [w for w in gw.getAllWindows()
                        if "chrome" in w.title.lower() and w.title.strip()]
                if wins:
                    hwnd_found = wins[0]._hWnd
                    user32.ShowWindow(hwnd_found, 9)   # SW_RESTORE
                    time.sleep(0.1)
                    user32.SetWindowPos(hwnd_found, 0,
                                        chrome_x, chrome_y, chrome_w, chrome_h,
                                        0x0040 | 0x0004 | 0x0020)
            except Exception:
                pass
            time.sleep(0.4)

    def _arrange():
        time.sleep(3)

        # Hammer Chrome into place for 10 seconds (it fights back after restore)
        threading.Thread(target=_move_chrome, daemon=True).start()

        # Claude and WhatsApp
        threading.Thread(target=_move_window,
                         args=("claude", claude_x, claude_y, claude_w, claude_h),
                         daemon=True).start()
        threading.Thread(target=_move_window,
                         args=("whatsapp", wa_x, wa_y, wa_w, wa_h),
                         daemon=True).start()

        # Dopamine video — fullscreen on laptop
        if dopamine_file:
            stem = os.path.splitext(os.path.basename(dopamine_file))[0]
            for title in [stem, "dopamine", "windows media player",
                          "movies & tv", "film & tv", "vlc", "video"]:
                if _move_window(title, lap_x, lap_y, lap_w, lap_h, fullscreen=True):
                    break

    threading.Thread(target=_arrange, daemon=True).start()

    video_msg = (f"and playing {os.path.basename(dopamine_file)} on the laptop screen"
                 if dopamine_file else "though I couldn't find the dopamine video")
    return (f"Setting up your work system, sir — Chrome and WhatsApp on the external screen "
            f"with Claude in the top-right, {video_msg}. Volume's at a hundred.")
