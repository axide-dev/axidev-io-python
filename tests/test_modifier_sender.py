from __future__ import annotations

import unittest
from unittest.mock import patch

from axidev_io._api import KeyboardKeyHelpers, KeyboardSender
from axidev_io._constants import Modifier


class ModifierSenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sender = KeyboardSender(lambda: None, KeyboardKeyHelpers())

    @patch("axidev_io._api._native.hold_modifiers", return_value=True)
    @patch("axidev_io._api._native.is_ready", return_value=True)
    def test_hold_modifiers_forwards_resolved_mask(self, _is_ready, hold_modifiers) -> None:
        self.sender.hold_modifiers(["Ctrl", "Shift"])

        hold_modifiers.assert_called_once_with(int(Modifier.CTRL | Modifier.SHIFT))

    @patch("axidev_io._api._native.release_modifiers", return_value=True)
    @patch("axidev_io._api._native.is_ready", return_value=True)
    def test_release_modifiers_forwards_resolved_mask(self, _is_ready, release_modifiers) -> None:
        self.sender.release_modifiers(["Alt", "Super"])

        release_modifiers.assert_called_once_with(int(Modifier.ALT | Modifier.SUPER))

    @patch("axidev_io._api._native.release_all_modifiers", return_value=True)
    @patch("axidev_io._api._native.is_ready", return_value=True)
    def test_release_all_modifiers_forwards_to_native(self, _is_ready, release_all_modifiers) -> None:
        self.sender.release_all_modifiers()

        release_all_modifiers.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
