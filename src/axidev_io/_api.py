from __future__ import annotations

import importlib.resources
import re
import subprocess
import sys
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from . import _native
from ._constants import (
    BACKEND_NAMES,
    LOG_LEVEL_NAMES,
    MODIFIER_ALIASES,
    MODIFIER_FLAGS,
    Backend,
    LogLevel,
    Modifier,
)
from ._errors import AxidevIoError, AxidevIoStateError


ModifierInput: TypeAlias = int | Modifier | str | Sequence[str] | None
LogLevelInput: TypeAlias = int | LogLevel | str
Listener: TypeAlias = Callable[["KeyEvent"], None]
Unsubscribe: TypeAlias = Callable[[], None]


@dataclass(frozen=True, slots=True)
class KeyCombo:
    key: int
    mods: int = 0


KeyInput: TypeAlias = int | str | KeyCombo | Mapping[str, object]


@dataclass(frozen=True, slots=True)
class Capabilities:
    can_inject_keys: bool
    can_inject_text: bool
    can_simulate_hid: bool
    supports_key_repeat: bool
    needs_accessibility_perm: bool
    needs_input_monitoring_perm: bool
    needs_uinput_access: bool


@dataclass(frozen=True, slots=True)
class KeyEvent:
    codepoint: int
    text: str | None
    key: int
    key_name: str | None
    mods: int
    modifiers: tuple[str, ...]
    combo: str | None
    pressed: bool


@dataclass(frozen=True, slots=True)
class KeyboardSenderStatus:
    initialized: bool
    ready: bool
    capabilities: Capabilities
    active_modifiers: int
    active_modifier_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class KeyboardListenerStatus:
    initialized: bool
    listening: bool
    subscriber_count: int


@dataclass(frozen=True, slots=True)
class PermissionSetupResult:
    platform: str
    already_granted: bool
    helper_applied: bool
    requires_logout: bool
    helper_path: str | None


@dataclass(frozen=True, slots=True)
class Status:
    version: str
    initialized: bool
    ready: bool
    listening: bool
    backend: int
    backend_name: str
    capabilities: Capabilities
    active_modifiers: int
    active_modifier_names: tuple[str, ...]
    log_level: int
    log_level_name: str
    sender: KeyboardSenderStatus
    listener: KeyboardListenerStatus


def _get_last_error() -> str | None:
    return _native.get_last_error()


def _make_error(action: str, fallback_details: str | None = None) -> AxidevIoError:
    return AxidevIoError(action, _get_last_error() or fallback_details)


def _assert_ok(action: str, ok: bool) -> None:
    if not ok:
        raise _make_error(action)


def _assert_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value


def _assert_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _capabilities_from_native(payload: Mapping[str, object]) -> Capabilities:
    return Capabilities(
        can_inject_keys=bool(payload["can_inject_keys"]),
        can_inject_text=bool(payload["can_inject_text"]),
        can_simulate_hid=bool(payload["can_simulate_hid"]),
        supports_key_repeat=bool(payload["supports_key_repeat"]),
        needs_accessibility_perm=bool(payload["needs_accessibility_perm"]),
        needs_input_monitoring_perm=bool(payload["needs_input_monitoring_perm"]),
        needs_uinput_access=bool(payload["needs_uinput_access"]),
    )


def _modifier_mask_to_names(mask: int) -> tuple[str, ...]:
    names = [name for name, flag in MODIFIER_FLAGS if (mask & flag) == flag]
    return tuple(names)


def _resolve_modifier_token(token: str) -> int:
    normalized = re.sub(r"[_\-\s]+", "", token.strip().lower())
    flag = MODIFIER_ALIASES.get(normalized)
    if flag is None:
        raise TypeError(f"Unknown modifier: {token}")
    return flag


def resolve_modifiers(mods: ModifierInput = None) -> int:
    if mods is None:
        return 0
    if isinstance(mods, Modifier):
        return int(mods)
    if isinstance(mods, int):
        return _assert_integer(mods, "mods")
    if isinstance(mods, str):
        segments = [segment.strip() for segment in mods.split("+") if segment.strip()]
        if not segments:
            return 0
        return sum(_resolve_modifier_token(segment) for segment in segments)
    if isinstance(mods, Sequence):
        mask = 0
        for segment in mods:
            if not isinstance(segment, str):
                raise TypeError("Modifier arrays must only contain strings")
            mask |= _resolve_modifier_token(segment)
        return mask
    raise TypeError("mods must be an integer, string, or sequence of strings")


def _resolve_log_level(level: LogLevelInput) -> int:
    if isinstance(level, LogLevel):
        return int(level)
    if isinstance(level, int):
        return _assert_integer(level, "log_level")

    normalized = level.strip().lower()
    for code, name in LOG_LEVEL_NAMES.items():
        if normalized == name:
            return code

    raise TypeError(f"Unknown log level: {level}")


def _ensure_keyboard_initialized(action: str) -> None:
    if not _native.is_ready():
        raise AxidevIoStateError(action)


class KeyboardModifierHelpers:
    flags = Modifier

    @staticmethod
    def resolve(mods: ModifierInput = None) -> int:
        return resolve_modifiers(mods)

    @staticmethod
    def to_names(mask: int) -> tuple[str, ...]:
        return _modifier_mask_to_names(_assert_integer(mask, "mask"))


class KeyboardComboHelpers:
    @staticmethod
    def parse(text: str) -> KeyCombo:
        return parse_combo(text)

    @staticmethod
    def format(input_value: KeyInput, mods: ModifierInput = None) -> str | None:
        return format_combo(input_value, mods)

    @staticmethod
    def resolve(input_value: KeyInput, mods: ModifierInput = None) -> KeyCombo:
        return normalize_key_input(input_value, mods)


class KeyboardKeyHelpers:
    def __init__(self) -> None:
        self.combo = KeyboardComboHelpers()
        self.modifiers = KeyboardModifierHelpers()

    @staticmethod
    def parse(text: str) -> int:
        return parse_key(text)

    @staticmethod
    def format(key: int) -> str | None:
        return format_key(key)

    @staticmethod
    def resolve(input_value: KeyInput, mods: ModifierInput = None) -> KeyCombo:
        return normalize_key_input(input_value, mods)

    @staticmethod
    def parse_combo(text: str) -> KeyCombo:
        return parse_combo(text)

    @staticmethod
    def format_combo(input_value: KeyInput, mods: ModifierInput = None) -> str | None:
        return format_combo(input_value, mods)


def parse_combo(text: str) -> KeyCombo:
    if not isinstance(text, str):
        raise TypeError("combo must be a string")

    parsed = _native.string_to_key_with_modifier(text)
    if not parsed or int(parsed["key"]) == 0:
        raise TypeError(f"Unknown key or combo: {text}")

    return KeyCombo(key=int(parsed["key"]), mods=int(parsed["mods"]))


def parse_key(text: str) -> int:
    parsed = parse_combo(text)
    if parsed.mods != int(Modifier.NONE):
        raise TypeError(f"Expected a plain key name without modifiers: {text}")
    return parsed.key


def format_key(key: int) -> str | None:
    return _native.key_to_string(_assert_integer(key, "key"))


def normalize_key_input(input_value: KeyInput, mods: ModifierInput = None) -> KeyCombo:
    if isinstance(input_value, int):
        return KeyCombo(
            key=_assert_integer(input_value, "key"),
            mods=resolve_modifiers(mods),
        )

    if isinstance(input_value, str):
        if mods is None:
            return parse_combo(input_value)
        return KeyCombo(key=parse_key(input_value), mods=resolve_modifiers(mods))

    if isinstance(input_value, KeyCombo):
        resolved_mods = input_value.mods if mods is None else resolve_modifiers(mods)
        return KeyCombo(key=_assert_integer(input_value.key, "key"), mods=resolved_mods)

    combo_input = _assert_mapping(input_value, "key input")
    if "key" not in combo_input:
        raise TypeError("key input mapping must contain a key value")

    key_value = combo_input["key"]
    key = parse_key(key_value) if isinstance(key_value, str) else _assert_integer(key_value, "key")
    raw_mods = combo_input.get("mods") if mods is None else mods
    return KeyCombo(key=key, mods=resolve_modifiers(raw_mods))


def format_combo(input_value: KeyInput, mods: ModifierInput = None) -> str | None:
    combo = normalize_key_input(input_value, mods)
    return _native.key_to_string_with_modifier(combo.key, combo.mods)


class KeyboardSender:
    def __init__(self, get_capabilities: Callable[[], Capabilities], keys: KeyboardKeyHelpers) -> None:
        self._get_capabilities = get_capabilities
        self._keys = keys

    @property
    def initialized(self) -> bool:
        return _native.is_ready()

    @property
    def ready(self) -> bool:
        return self.initialized

    @property
    def capabilities(self) -> Capabilities:
        return self._get_capabilities()

    @property
    def active_modifiers(self) -> int:
        return self.get_active_modifiers()

    @property
    def active_modifier_names(self) -> tuple[str, ...]:
        return self.get_active_modifier_names()

    def is_initialized(self) -> bool:
        return self.initialized

    def get_capabilities(self) -> Capabilities:
        return self._get_capabilities()

    def get_active_modifiers(self) -> int:
        return _native.active_modifiers()

    def get_active_modifier_names(self) -> tuple[str, ...]:
        return _modifier_mask_to_names(self.get_active_modifiers())

    def status(self) -> KeyboardSenderStatus:
        return KeyboardSenderStatus(
            initialized=self.initialized,
            ready=self.ready,
            capabilities=self.capabilities,
            active_modifiers=self.active_modifiers,
            active_modifier_names=self.active_modifier_names,
        )

    def key_down(self, input_value: KeyInput, mods: ModifierInput = None) -> None:
        _ensure_keyboard_initialized("keyboard.sender.key_down")
        combo = self._keys.resolve(input_value, mods)
        _assert_ok("key_down", _native.key_down(combo.key, combo.mods))

    def key_up(self, input_value: KeyInput, mods: ModifierInput = None) -> None:
        _ensure_keyboard_initialized("keyboard.sender.key_up")
        combo = self._keys.resolve(input_value, mods)
        _assert_ok("key_up", _native.key_up(combo.key, combo.mods))

    def tap(self, input_value: KeyInput, mods: ModifierInput = None) -> None:
        _ensure_keyboard_initialized("keyboard.sender.tap")
        combo = self._keys.resolve(input_value, mods)
        _assert_ok("tap", _native.tap(combo.key, combo.mods))

    def hold_modifiers(self, mods: ModifierInput) -> None:
        _ensure_keyboard_initialized("keyboard.sender.hold_modifiers")
        _assert_ok("hold_modifiers", _native.hold_modifiers(resolve_modifiers(mods)))

    def release_modifiers(self, mods: ModifierInput) -> None:
        _ensure_keyboard_initialized("keyboard.sender.release_modifiers")
        _assert_ok(
            "release_modifiers",
            _native.release_modifiers(resolve_modifiers(mods)),
        )

    def release_all_modifiers(self) -> None:
        _ensure_keyboard_initialized("keyboard.sender.release_all_modifiers")
        _assert_ok("release_all_modifiers", _native.release_all_modifiers())

    def type_text(self, text: str) -> None:
        _ensure_keyboard_initialized("keyboard.sender.type_text")
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        _assert_ok("type_text", _native.type_text(text))

    def type_character(self, input_value: int | str) -> None:
        _ensure_keyboard_initialized("keyboard.sender.type_character")
        if isinstance(input_value, str):
            if len(input_value) != 1:
                raise TypeError("type_character expects a single Unicode character")
            codepoint = ord(input_value)
        else:
            codepoint = _assert_integer(input_value, "codepoint")
        _assert_ok("type_character", _native.type_character(codepoint))

    def flush(self) -> None:
        _ensure_keyboard_initialized("keyboard.sender.flush")
        _native.flush()

    def set_key_delay(self, delay_us: int) -> None:
        _ensure_keyboard_initialized("keyboard.sender.set_key_delay")
        _native.set_key_delay(_assert_integer(delay_us, "delay_us"))

    press = key_down
    release = key_up
    text = type_text
    character = type_character


class KeyboardListener:
    def __init__(self) -> None:
        self._listeners: set[Listener] = set()
        self._native_listener_running = False

    @property
    def initialized(self) -> bool:
        return _native.is_ready()

    @property
    def listening(self) -> bool:
        return self.is_listening()

    @property
    def subscriber_count(self) -> int:
        return len(self._listeners)

    def is_initialized(self) -> bool:
        return self.initialized

    def is_listening(self) -> bool:
        return self._native_listener_running and _native.is_listening()

    def _decorate_listener_event(self, raw_event: Mapping[str, object]) -> KeyEvent:
        codepoint = int(raw_event["codepoint"])
        key = int(raw_event["key"])
        mods = int(raw_event["mods"])
        return KeyEvent(
            codepoint=codepoint,
            text=chr(codepoint) if codepoint > 0 else None,
            key=key,
            key_name=_native.key_to_string(key),
            mods=mods,
            modifiers=_modifier_mask_to_names(mods),
            combo=_native.key_to_string_with_modifier(key, mods),
            pressed=bool(raw_event["pressed"]),
        )

    def _emit_listener_event(self, raw_event: Mapping[str, object]) -> None:
        event = self._decorate_listener_event(raw_event)
        for listener in tuple(self._listeners):
            try:
                listener(event)
            except Exception as exc:  # pragma: no cover - user callback failure path
                warnings.warn(
                    str(exc),
                    RuntimeWarning,
                    stacklevel=1,
                )

    def start(self, listener: Listener) -> Unsubscribe:
        if not callable(listener):
            raise TypeError("listener must be callable")

        _ensure_keyboard_initialized("keyboard.listener.start")

        if not self._native_listener_running:
            _assert_ok("start_listener", _native.start_listener(self._emit_listener_event))
            self._native_listener_running = True

        self._listeners.add(listener)
        active = True

        def unsubscribe() -> None:
            nonlocal active
            if not active:
                return
            active = False
            self._listeners.discard(listener)
            if not self._listeners:
                self.stop()

        return unsubscribe

    def stop(self) -> None:
        self._listeners.clear()
        _native.stop_listener()
        self._native_listener_running = False

    def status(self) -> KeyboardListenerStatus:
        return KeyboardListenerStatus(
            initialized=self.initialized,
            listening=self.listening,
            subscriber_count=self.subscriber_count,
        )

    listen = start
    subscribe = start


class PermissionHelpers:
    def __init__(self, keyboard: "Keyboard") -> None:
        self._keyboard = keyboard

    def request(self) -> None:
        self._keyboard.request_permissions()

    def setup(self) -> PermissionSetupResult:
        return self._keyboard.setup_permissions()

    def has_required(self) -> bool:
        return self._keyboard.has_required_permissions()

    def check(self) -> bool:
        return self._keyboard.has_required_permissions()


class Keyboard:
    def __init__(self) -> None:
        self.keys = KeyboardKeyHelpers()
        self.modifiers = self.keys.modifiers
        self.sender = KeyboardSender(self.get_capabilities, self.keys)
        self.listener = KeyboardListener()
        self.permissions = PermissionHelpers(self)

    @property
    def initialized(self) -> bool:
        return self.is_ready()

    @property
    def ready(self) -> bool:
        return self.is_ready()

    @property
    def backend(self) -> int:
        return self.get_backend()

    @property
    def backend_name(self) -> str:
        return self.get_backend_name()

    @property
    def capabilities(self) -> Capabilities:
        return self.get_capabilities()

    @property
    def log_level(self) -> int:
        return self.get_log_level()

    @property
    def log_level_name(self) -> str:
        return self.get_log_level_name()

    def is_ready(self) -> bool:
        return _native.is_ready()

    def is_initialized(self) -> bool:
        return self.is_ready()

    def get_backend(self) -> int:
        return _native.get_backend()

    def get_backend_name(self, backend: int | None = None) -> str:
        value = self.get_backend() if backend is None else _assert_integer(backend, "backend")
        return BACKEND_NAMES.get(value, "unknown")

    def get_capabilities(self) -> Capabilities:
        return _capabilities_from_native(_native.get_capabilities())

    def get_log_level(self) -> int:
        return _native.log_get_level()

    def get_log_level_name(self, level: int | None = None) -> str:
        value = self.get_log_level() if level is None else _assert_integer(level, "level")
        return LOG_LEVEL_NAMES.get(value, "unknown")

    def set_log_level(self, level: LogLevelInput) -> None:
        _native.log_set_level(_resolve_log_level(level))

    def version(self) -> str:
        return _native.version()

    def get_last_error(self) -> str | None:
        return _get_last_error()

    def clear_last_error(self) -> None:
        _native.clear_last_error()

    def initialize(
        self,
        options: Mapping[str, object] | None = None,
        /,
        *,
        key_delay_us: int | None = None,
        log_level: LogLevelInput | None = None,
    ) -> "Keyboard":
        if options is not None:
            if key_delay_us is not None or log_level is not None:
                raise TypeError("Pass either options or keyword arguments, not both")
            options = _assert_mapping(options, "options")
            if "key_delay_us" in options:
                key_delay_us = _assert_integer(options["key_delay_us"], "key_delay_us")
            elif "keyDelayUs" in options:
                key_delay_us = _assert_integer(options["keyDelayUs"], "keyDelayUs")
            if "log_level" in options:
                log_level = options["log_level"]  # type: ignore[assignment]
            elif "logLevel" in options:
                log_level = options["logLevel"]  # type: ignore[assignment]

        if log_level is not None:
            self.set_log_level(log_level)

        _assert_ok("initialize", _native.initialize())

        if key_delay_us is not None:
            _native.set_key_delay(_assert_integer(key_delay_us, "key_delay_us"))

        return self

    def shutdown(self) -> None:
        self.listener.stop()
        _native.free()

    free = shutdown

    def request_permissions(self) -> None:
        _assert_ok("request_permissions", _native.request_permissions())

    def has_required_permissions(self) -> bool:
        initialized_here = False
        try:
            if not self.is_ready():
                self.initialize()
                initialized_here = True
            self.request_permissions()
            return True
        except AxidevIoError as exc:
            if sys.platform.startswith("linux") and exc.action in {"initialize", "request_permissions"}:
                return False
            raise
        finally:
            if initialized_here:
                self.shutdown()

    def _linux_permission_helper_path(self) -> Path:
        return (
            importlib.resources.files("axidev_io")
            .joinpath("vendor", "axidev-io", "scripts", "setup_uinput_permissions.sh")
        )

    def _run_linux_permission_helper(self) -> str:
        helper_path = self._linux_permission_helper_path()
        if not helper_path.is_file():
            raise AxidevIoError(
                "setup_permissions",
                f"Linux permission helper not found at {helper_path}",
            )

        try:
            completed = subprocess.run([str(helper_path)], check=True)
        except subprocess.CalledProcessError as exc:
            raise AxidevIoError(
                "setup_permissions",
                f"Linux permission helper exited with status {exc.returncode}",
            ) from exc
        except OSError as exc:
            raise AxidevIoError("setup_permissions", str(exc)) from exc

        return str(helper_path)

    def setup_permissions(self) -> PermissionSetupResult:
        if not sys.platform.startswith("linux"):
            self.has_required_permissions()
            return PermissionSetupResult(
                platform=sys.platform,
                already_granted=True,
                helper_applied=False,
                requires_logout=False,
                helper_path=None,
            )

        if self.has_required_permissions():
            return PermissionSetupResult(
                platform="linux",
                already_granted=True,
                helper_applied=False,
                requires_logout=False,
                helper_path=None,
            )

        return PermissionSetupResult(
            platform="linux",
            already_granted=False,
            helper_applied=True,
            requires_logout=True,
            helper_path=self._run_linux_permission_helper(),
        )

    def status(self) -> Status:
        sender_status = self.sender.status()
        listener_status = self.listener.status()
        backend = self.get_backend()
        return Status(
            version=self.version(),
            initialized=self.is_ready(),
            ready=self.is_ready(),
            listening=listener_status.listening,
            backend=backend,
            backend_name=self.get_backend_name(backend),
            capabilities=self.get_capabilities(),
            active_modifiers=sender_status.active_modifiers,
            active_modifier_names=sender_status.active_modifier_names,
            log_level=self.get_log_level(),
            log_level_name=self.get_log_level_name(),
            sender=sender_status,
            listener=listener_status,
        )


keyboard = Keyboard()
keys = keyboard.keys
modifiers = keyboard.modifiers

clear_last_error = keyboard.clear_last_error
flush = keyboard.sender.flush
free = keyboard.free
get_active_modifier_names = keyboard.sender.get_active_modifier_names
get_active_modifiers = keyboard.sender.get_active_modifiers
get_backend = keyboard.get_backend
get_backend_name = keyboard.get_backend_name
get_capabilities = keyboard.get_capabilities
get_last_error = keyboard.get_last_error
get_log_level = keyboard.get_log_level
get_log_level_name = keyboard.get_log_level_name
has_required_permissions = keyboard.has_required_permissions
hold_modifiers = keyboard.sender.hold_modifiers
initialize = keyboard.initialize
is_listening = keyboard.listener.is_listening
is_ready = keyboard.is_ready
key_down = keyboard.sender.key_down
key_up = keyboard.sender.key_up
listen = keyboard.listener.listen
release_all_modifiers = keyboard.sender.release_all_modifiers
release_modifiers = keyboard.sender.release_modifiers
request_permissions = keyboard.request_permissions
set_key_delay = keyboard.sender.set_key_delay
set_log_level = keyboard.set_log_level
setup_permissions = keyboard.setup_permissions
shutdown = keyboard.shutdown
start_listener = keyboard.listener.start
status = keyboard.status
stop_listener = keyboard.listener.stop
tap = keyboard.sender.tap
type_character = keyboard.sender.type_character
type_text = keyboard.sender.type_text
version = keyboard.version
