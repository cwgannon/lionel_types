"""End-to-end check of the Windows keyboard lock, for CI.

Starts the real full-screen app, presses the Windows key, Alt+Tab, Print Screen,
Ctrl+Esc and Shift x5 with SendInput, and checks the app intercepted them and put
the Sticky Keys setting back afterwards.

This takes over the screen for several seconds, so it only runs in CI unless you
pass --on-my-desktop. Keys are only sent while the app's own window is in front.

    python tools/check_windows_lock.py [screenshot.png] [--on-my-desktop]
"""

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):  # only here so INPUT has the right size
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


EXTENDED_KEYS = {0x5B, 0x5C, 0x2C}
VK_SHIFT, VK_CONTROL, VK_ALT, VK_TAB, VK_ESC, VK_PRTSC, VK_LWIN = 0x10, 0x11, 0xA4, 0x09, 0x1B, 0x2C, 0x5B


def send(vk: int, up: bool = False) -> None:
    flags = (2 if up else 0) | (1 if vk in EXTENDED_KEYS else 0)
    event = INPUT(type=1, u=_INPUTUNION(ki=KEYBDINPUT(wVk=vk, dwFlags=flags)))
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    time.sleep(0.06)


def tap(vk: int, holding: int = 0) -> None:
    if holding:
        send(holding)
    send(vk)
    send(vk, up=True)
    if holding:
        send(holding, up=True)


def sticky_keys_flags() -> int:
    class STICKYKEYS(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwFlags", wintypes.DWORD)]

    value = STICKYKEYS(cbSize=8)
    user32.SystemParametersInfoW(0x3A, 8, ctypes.byref(value), 0)
    return value.dwFlags


def foreground_pid() -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


def screenshot(path: str) -> None:
    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    "Add-Type -AssemblyName System.Windows.Forms, System.Drawing;"
                    "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
                    "$m=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
                    "[System.Drawing.Graphics]::FromImage($m).CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
                    f"$m.Save('{path}')"], timeout=30, check=False)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not os.environ.get("CI") and "--on-my-desktop" not in sys.argv:
        print("This takes over the screen for a few seconds; pass --on-my-desktop to run it outside CI.")
        return 2

    sticky_before = sticky_keys_flags()
    app = subprocess.Popen([sys.executable, "-m", "lionel_types", "--self-test", "10", "--mute"],
                           cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + 8
    while time.time() < deadline and foreground_pid() != app.pid:
        time.sleep(0.1)
    in_front = foreground_pid() == app.pid
    if in_front:
        time.sleep(1.0)
        tap(VK_LWIN)  # Start menu
        tap(VK_TAB, holding=VK_ALT)  # switch apps
        tap(VK_PRTSC)  # Snipping Tool
        tap(VK_ESC, holding=VK_CONTROL)  # Start menu
        for _ in range(5):
            tap(VK_SHIFT)  # Sticky Keys dialog
        time.sleep(0.7)
        in_front = foreground_pid() == app.pid
        if in_front and args:
            screenshot(str(Path(args[0]).resolve()))
    try:
        output, _ = app.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        app.kill()
        output, _ = app.communicate()
        print("FAIL: the app did not quit by itself")
        return 1
    print(output)

    problems = []
    if not in_front:
        problems.append("the app window was not in front, so no keys could be tested")
    intercepted = next((line for line in output.splitlines() if "Keys intercepted:" in line), "")
    for label in ("WIN", "ALT", "PRTSC", "ESC"):
        if label not in intercepted:
            problems.append(f"{label} was not intercepted")
    if sticky_keys_flags() != sticky_before:
        problems.append("the Sticky Keys setting was not restored")
    for problem in problems:
        print("FAIL:", problem)
    if not problems:
        print("OK: Windows key, Alt, Print Screen and Esc were all kept inside the app.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
