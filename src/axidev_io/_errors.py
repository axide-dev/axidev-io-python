from __future__ import annotations


class AxidevIoError(Exception):
    def __init__(self, action: str, details: str | None = None) -> None:
        message = f"{action} failed"
        if details:
            message = f"{message}: {details}"
        super().__init__(message)
        self.action = action
        self.details = details


class AxidevIoStateError(Exception):
    code = "AXIDEV_IO_NOT_INITIALIZED"

    def __init__(
        self,
        action: str,
        details: str = "keyboard.initialize() to be called first",
    ) -> None:
        super().__init__(f"{action} requires {details}")
        self.action = action
        self.details = details
