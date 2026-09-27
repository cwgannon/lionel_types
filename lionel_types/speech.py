"""Say letters and words out loud using the computer's built-in voice.

No extra packages: Windows uses the System.Speech voice through one long-lived
PowerShell process, macOS uses ``say``, and Linux uses ``spd-say``/``espeak``
if one is installed. New speech always interrupts old speech, so a mashing
kid hears the latest key rather than a growing backlog.
"""

from __future__ import annotations

import base64
import re
import shutil
import subprocess
import sys
from typing import List, Optional

_UNSAFE = re.compile(r"[^\w .,!?'-]")


def clean(text: str) -> str:
    """Keep speech to plain words so it can never be read as a command-line option."""
    return _UNSAFE.sub(" ", text).strip().lstrip("-")


class Speaker:
    """Speaks nothing. The base for real voices, and the fallback when none is available."""

    def say(self, text: str) -> None:
        pass

    def close(self) -> None:
        pass


_POWERSHELL_LOOP = r"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Speech
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice.Rate = -1
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
while ($null -ne ($line = [Console]::In.ReadLine())) {
    $voice.SpeakAsyncCancelAll()
    if ($line) { [void]$voice.SpeakAsync($line) }
}
"""


class WindowsSpeaker(Speaker):
    """Feeds lines to a hidden PowerShell process that speaks each one."""

    def __init__(self) -> None:
        script = base64.b64encode(_POWERSHELL_LOOP.encode("utf-16-le")).decode("ascii")
        self._proc: Optional[subprocess.Popen] = subprocess.Popen(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-EncodedCommand", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def say(self, text: str) -> None:
        if self._proc is None or self._proc.stdin is None:
            return
        try:
            self._proc.stdin.write((clean(text) + "\n").encode("utf-8"))
            self._proc.stdin.flush()
        except OSError:  # the voice process died; carry on silently
            self._proc = None

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            self._proc.kill()
        self._proc = None


class CommandSpeaker(Speaker):
    """Runs a speech command per utterance, stopping the previous one first."""

    def __init__(self, command: List[str]) -> None:
        self._command = command
        self._proc: Optional[subprocess.Popen] = None

    def say(self, text: str) -> None:
        text = clean(text)
        if not text:
            return
        self._stop()
        try:
            self._proc = subprocess.Popen(
                self._command + [text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except OSError:
            self._proc = None

    def _stop(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()

    def close(self) -> None:
        self._stop()


def create() -> Speaker:
    """The best available voice for this computer."""
    try:
        if sys.platform == "win32":
            return WindowsSpeaker()
        if sys.platform == "darwin":
            return CommandSpeaker(["say", "-r", "170"])
        if shutil.which("spd-say"):
            return CommandSpeaker(["spd-say", "-w"])
        if shutil.which("espeak"):
            return CommandSpeaker(["espeak"])
    except OSError:
        pass
    return Speaker()
