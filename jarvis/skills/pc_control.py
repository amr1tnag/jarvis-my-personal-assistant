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
    # Claude desktop — search common install locations
    "claude":             (_p(_LOCAL, "AnthropicClaude", "claude.exe") or
                           _find_exe(_LOCAL, "claude.exe") or
                           _p(_PROG, "Anthropic", "Claude", "Claude.exe") or
                           "claude:"),
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


def work_setup() -> str:
    """
    Set up Amrit's work system:
    - External monitor (left): Chrome (left 60%), Claude (top-right), WhatsApp (bottom-right)
    - Laptop screen (right): dopamine video fullscreen
    - Volume: 100%
    """
    import threading

    set_volume(100)

    ext, lap = _get_monitors()

    # Layout on external monitor (-1920, -316) 1920x1080
    # Chrome: full left 60% of external
    chrome_x, chrome_y = ext.x, ext.y
    chrome_w, chrome_h = int(ext.width * 0.6), ext.height
    # Claude: top-right 40% of external
    claude_x, claude_y = ext.x + int(ext.width * 0.6), ext.y
    claude_w, claude_h = int(ext.width * 0.4), ext.height // 2
    # WhatsApp: bottom-right 40% of external
    wa_x, wa_y = ext.x + int(ext.width * 0.6), ext.y + ext.height // 2
    wa_w, wa_h = int(ext.width * 0.4), ext.height // 2

    # Find dopamine video before launching anything
    video_extensions = (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm")
    dopamine_file = None
    for folder in [os.path.join(os.path.expanduser("~"), "Downloads"),
                   os.path.join(os.path.expanduser("~"), "Desktop")]:
        for f in os.listdir(folder):
            if "dopamine" in f.lower() and f.lower().endswith(video_extensions):
                dopamine_file = os.path.join(folder, f)
                break
        if dopamine_file:
            break

    # Launch Chrome with explicit window position/size flags (most reliable)
    chrome_exe = APP_MAP.get("chrome", "chrome")
    chrome_flags = [
        "--profile-directory=Default",
        f"--window-position={chrome_x},{chrome_y}",
        f"--window-size={chrome_w},{chrome_h}",
    ]
    def _launch_chrome():
        try:
            if os.path.isfile(chrome_exe):
                subprocess.Popen([chrome_exe] + chrome_flags,
                                 creationflags=subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen(["chrome"] + chrome_flags,
                                 shell=True, creationflags=subprocess.DETACHED_PROCESS)
        except Exception:
            open_application("chrome")

    threading.Thread(target=_launch_chrome, daemon=True).start()

    # Launch Claude and WhatsApp
    for app in ("claude", "whatsapp"):
        threading.Thread(target=open_application, args=(app,), daemon=True).start()

    # Play dopamine video
    if dopamine_file:
        def _play_video():
            os.startfile(dopamine_file)
            time.sleep(2)
            set_volume(100)
        threading.Thread(target=_play_video, daemon=True).start()

    # Arrange windows after apps load
    def _arrange():
        # Chrome: give it a moment to open with its flags, then nudge it into place
        time.sleep(3)
        _move_window("chrome", chrome_x, chrome_y, chrome_w, chrome_h)

        # Claude and WhatsApp: wait for them to appear then position
        threading.Thread(target=_move_window,
                         args=("claude", claude_x, claude_y, claude_w, claude_h),
                         daemon=True).start()
        threading.Thread(target=_move_window,
                         args=("whatsapp", wa_x, wa_y, wa_w, wa_h),
                         daemon=True).start()

        # Video player — fullscreen on laptop screen
        if dopamine_file:
            video_title_hints = [
                os.path.splitext(os.path.basename(dopamine_file))[0],
                "windows media player", "movies & tv", "film & tv",
                "vlc", "video", "dopamine",
            ]
            for title in video_title_hints:
                if _move_window(title, lap.x, lap.y, lap.width, lap.height,
                                fullscreen=True):
                    break

    threading.Thread(target=_arrange, daemon=True).start()

    video_msg = f"and playing {os.path.basename(dopamine_file)} on the laptop screen" if dopamine_file else "though I couldn't find the dopamine video on the Desktop"
    return f"Setting up your work system, sir — Chrome, Claude, and WhatsApp on the external screen, {video_msg}. Volume's at a hundred."
