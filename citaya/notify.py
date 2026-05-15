import logging
import platform
import subprocess
import sys
from shutil import which

_notifiers = None


def _find_notifiers():
    available = []

    system = platform.system()

    if system == "Darwin":
        available.append(_macos_speak)
        available.append(_macos_notification)
    elif system == "Windows":
        if which("wsay"):
            available.append(_wsay_speak)
    else:
        if which("espeak"):
            available.append(_espeak_speak)
        if which("notify-send"):
            available.append(_linux_notification)

    available.append(_terminal_bell)

    return available


def _macos_speak(phrase):
    subprocess.Popen(["say", phrase], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _macos_notification(phrase):
    script = f'display notification "{phrase}" with title "CitaYa"'
    subprocess.Popen(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _espeak_speak(phrase):
    subprocess.Popen(["espeak", phrase], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _linux_notification(phrase):
    subprocess.Popen(
        ["notify-send", "CitaYa", phrase],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wsay_speak(phrase):
    subprocess.Popen(["wsay", phrase], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _terminal_bell(_phrase):
    sys.stdout.write("\a")
    sys.stdout.flush()


def notify(phrase: str):
    global _notifiers
    if _notifiers is None:
        _notifiers = _find_notifiers()

    for fn in _notifiers:
        try:
            fn(phrase)
        except Exception as e:
            logging.debug(f"Notifier {fn.__name__} failed: {e}")
