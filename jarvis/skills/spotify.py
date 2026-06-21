import subprocess


def _media_key(key_code: int):
    """Send a media key via PowerShell WScript.Shell."""
    script = f"$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]{key_code})"
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", script],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def spotify_play_pause() -> str:
    _media_key(179)
    return "Toggled play/pause, sir."


def spotify_next() -> str:
    _media_key(176)
    return "Skipping to the next track, sir."


def spotify_previous() -> str:
    _media_key(177)
    return "Going back to the previous track, sir."


def spotify_volume_up() -> str:
    for _ in range(5):
        _media_key(175)   # VK_VOLUME_UP
    return "Turned Spotify up, sir."


def spotify_volume_down() -> str:
    for _ in range(5):
        _media_key(174)   # VK_VOLUME_DOWN
    return "Turned it down, sir."
