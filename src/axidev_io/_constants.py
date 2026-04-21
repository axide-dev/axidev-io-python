from __future__ import annotations

from enum import IntEnum, IntFlag


class Modifier(IntFlag):
    NONE = 0x00
    SHIFT = 0x01
    CTRL = 0x02
    ALT = 0x04
    SUPER = 0x08
    CAPSLOCK = 0x10
    NUMLOCK = 0x20


class Backend(IntEnum):
    UNKNOWN = 0
    WINDOWS = 1
    MACOS = 2
    LINUX_LIBINPUT = 3
    LINUX_UINPUT = 4


class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3


BACKEND_NAMES: dict[int, str] = {
    int(Backend.UNKNOWN): "unknown",
    int(Backend.WINDOWS): "windows",
    int(Backend.MACOS): "macos",
    int(Backend.LINUX_LIBINPUT): "linux-libinput",
    int(Backend.LINUX_UINPUT): "linux-uinput",
}

LOG_LEVEL_NAMES: dict[int, str] = {
    int(LogLevel.DEBUG): "debug",
    int(LogLevel.INFO): "info",
    int(LogLevel.WARN): "warn",
    int(LogLevel.ERROR): "error",
}

MODIFIER_FLAGS: tuple[tuple[str, int], ...] = (
    ("Super", int(Modifier.SUPER)),
    ("Ctrl", int(Modifier.CTRL)),
    ("Alt", int(Modifier.ALT)),
    ("Shift", int(Modifier.SHIFT)),
    ("CapsLock", int(Modifier.CAPSLOCK)),
    ("NumLock", int(Modifier.NUMLOCK)),
)

MODIFIER_ALIASES: dict[str, int] = {
    "": int(Modifier.NONE),
    "none": int(Modifier.NONE),
    "shift": int(Modifier.SHIFT),
    "ctrl": int(Modifier.CTRL),
    "control": int(Modifier.CTRL),
    "alt": int(Modifier.ALT),
    "option": int(Modifier.ALT),
    "super": int(Modifier.SUPER),
    "meta": int(Modifier.SUPER),
    "cmd": int(Modifier.SUPER),
    "command": int(Modifier.SUPER),
    "win": int(Modifier.SUPER),
    "windows": int(Modifier.SUPER),
    "caps": int(Modifier.CAPSLOCK),
    "capslock": int(Modifier.CAPSLOCK),
    "num": int(Modifier.NUMLOCK),
    "numlock": int(Modifier.NUMLOCK),
}
