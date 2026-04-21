# axidev-io

`axidev-io` is a Python package for keyboard automation and global keyboard event listening.

It wraps the native `axidev-io` library and keeps the same high-level shape as the JS bindings:

- `keyboard.initialize(...)`
- `keyboard.sender.tap(...)`
- `keyboard.sender.type_text(...)`
- `keyboard.listener.start(...)`
- `keyboard.keys.parse(...)`
- `keyboard.setup_permissions()`

The PyPI distribution name is `axidev-io`.
The Python import name is `axidev_io`.

## Install

```sh
pip install axidev-io
```

The source distribution builds the native extension from vendored `axidev-io` C sources.

## Platform Notes

Supported platforms:

- Linux
- Windows

### Linux

Build-time requirements:

- `pkg-config`
- development packages for `libinput`, `libudev`, and `xkbcommon`
- a working C toolchain

Runtime requirements:

- system shared libraries for `libinput`, `libudev`, and `xkbcommon`
- access to `/dev/uinput` for key injection
- access to the relevant `/dev/input/event*` devices for listening

Those Linux backend dependencies are intentionally expected from the system and must remain dynamically linked for legal/compliance reasons.

### Windows

Windows builds use the normal Python extension toolchain and link against system Win32 libraries.

## Simple Example

```python
from axidev_io import keyboard

permissions = keyboard.setup_permissions()

if permissions.requires_logout:
    print("Log out and back in, then run again.")
    raise SystemExit(0)

keyboard.initialize(key_delay_us=2000)

keyboard.sender.type_text("Hello from axidev-io")
keyboard.sender.tap("Ctrl+Shift+P")

stop = keyboard.listener.start(lambda event: print(event.combo, event.pressed, event.text))

try:
    ...
finally:
    stop()
    keyboard.shutdown()
```

## API Shape

Main entrypoints:

- `keyboard.initialize(...)`
- `keyboard.shutdown()`
- `keyboard.setup_permissions()`
- `keyboard.status()`
- `keyboard.version()`

Sender methods:

- `keyboard.sender.tap(input, mods=None)`
- `keyboard.sender.key_down(input, mods=None)`
- `keyboard.sender.key_up(input, mods=None)`
- `keyboard.sender.type_text(text)`
- `keyboard.sender.type_character(input)`
- `keyboard.sender.hold_modifiers(mods)`
- `keyboard.sender.release_modifiers(mods)`
- `keyboard.sender.release_all_modifiers()`
- `keyboard.sender.flush()`

Listener methods:

- `keyboard.listener.start(callback)`
- `keyboard.listener.stop()`

Key helpers:

- `keyboard.keys.parse(name)`
- `keyboard.keys.format(key)`
- `keyboard.keys.parse_combo(text)`
- `keyboard.keys.format_combo(input, mods=None)`
- `keyboard.keys.modifiers.resolve(mods)`
- `keyboard.keys.modifiers.to_names(mask)`

## Shipped Compliance Assets

The installed package ships the upstream consumer and license material under `axidev_io/vendor/axidev-io/`, including:

- `docs/consumers/README.md`
- `scripts/setup_uinput_permissions.sh`
- `LICENSE`
- `vendor/licenses/stb.txt`

## Development

Useful local commands:

```sh
python scripts/sync_upstream.py
python -m pip install -e .
python -m build
```
