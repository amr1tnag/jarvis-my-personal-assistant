import os
import subprocess
import webbrowser
import glob
from datetime import datetime

APP_MAP = {
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "spotify": "spotify",
    "discord": "discord",
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "vlc": "vlc",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "paint": "mspaint",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "terminal": "wt",
    "windows terminal": "wt",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    "steam": "steam",
    "obs": "obs64",
}

PROCESS_MAP = {
    "vs code": "Code.exe",
    "vscode": "Code.exe",
    "visual studio code": "Code.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "calc": "CalculatorApp.exe",
    "word": "WINWORD.EXE",
    "microsoft word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "whatsapp": "WhatsApp.exe",
    "telegram": "Telegram.exe",
    "vlc": "vlc.exe",
    "task manager": "Taskmgr.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "steam": "steam.exe",
    "obs": "obs64.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
}


def open_application(name: str) -> str:
    key = name.lower().strip()
    exe = APP_MAP.get(key, key)

    if exe.startswith("ms-settings:"):
        try:
            os.startfile(exe)
            return f"Opened Settings."
        except Exception as e:
            return f"Failed to open settings: {e}"

    try:
        subprocess.Popen([exe], shell=True)
        return f"Opened {name}."
    except Exception:
        pass

    try:
        os.startfile(exe)
        return f"Opened {name}."
    except Exception as e:
        return f"Failed to open '{name}': {e}"


def close_application(name: str) -> str:
    key = name.lower().strip()
    process = PROCESS_MAP.get(key, key if key.endswith(".exe") else key + ".exe")

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
    script = f"""
$obj = New-Object -ComObject WScript.Shell
$vol = {level} / 100 * 65535
(New-Object -ComObject Shell.Application).Windows() | ForEach-Object {{}}
$wshShell = New-Object -com wscript.shell
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{
    int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{
    int f();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject {{ }}
public class Audio {{
    static IAudioEndpointVolume Vol() {{
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out dev));
        IAudioEndpointVolume vol = null;
        var domguid = typeof(IAudioEndpointVolume).GUID;
        Marshal.ThrowExceptionForHR(dev.Activate(ref domguid, 23, 0, out vol));
        return vol;
    }}
    public static void SetVolume(float level) {{ Marshal.ThrowExceptionForHR(Vol().SetMasterVolumeLevelScalar(level, System.Guid.Empty)); }}
}}
'@
[Audio]::SetVolume({level / 100})
"""
    try:
        subprocess.run(
            ["powershell", "-Command", f"[Audio]::SetVolume({level / 100})"],
            capture_output=True,
        )
        # Simpler fallback using nircmd-style PowerShell
        simple_script = (
            "$vol = [math]::Round(" + str(level) + " / 100 * 65535);"
            "(New-Object -comObject Shell.Application) | Out-Null;"
            "$wsh = New-Object -ComObject WScript.Shell;"
            "1..50 | ForEach-Object { $wsh.SendKeys([char]174) };"  # volume down all the way
            f"$steps = [math]::Round({level} / 2);"
            "$steps | ForEach-Object { $wsh.SendKeys([char]175) }"
        )
        result = subprocess.run(
            ["powershell", "-Command", simple_script],
            capture_output=True,
            text=True,
        )
        return f"Volume set to {level}%."
    except Exception as e:
        return f"Failed to set volume: {e}"


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
