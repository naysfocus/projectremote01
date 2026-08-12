import unittest
from unittest.mock import patch

from services import scrcpy


class WindowsPasteTests(unittest.TestCase):
    def test_window_not_found(self):
        with patch.object(scrcpy, "_windows_find_window", return_value=None):
            result = scrcpy._paste_clipboard_windows("RemoteHP-Mirror: HP", 0)
        self.assertFalse(result["ok"])
        self.assertFalse(result["focused"])
        self.assertFalse(result["pasted"])
        self.assertIn("Buka Mirror", result["error"])

    def test_native_paste_success_without_subprocess(self):
        with patch.object(scrcpy, "_windows_find_window", return_value=123), \
             patch.object(scrcpy, "_windows_focus_hwnd", return_value=True), \
             patch.object(scrcpy, "_windows_send_ctrl_v", return_value=True), \
             patch.object(scrcpy.subprocess, "run") as subprocess_run:
            result = scrcpy._paste_clipboard_windows("RemoteHP-Mirror: HP", 0)

        self.assertEqual(
            result,
            {"ok": True, "focused": True, "pasted": True, "error": None},
        )
        subprocess_run.assert_not_called()

    def test_focus_failure_stops_before_paste(self):
        with patch.object(scrcpy, "_windows_find_window", return_value=123), \
             patch.object(scrcpy, "_windows_focus_hwnd", return_value=False), \
             patch.object(scrcpy, "_windows_send_ctrl_v") as send_ctrl_v:
            result = scrcpy._paste_clipboard_windows("RemoteHP-Mirror: HP", 0)

        self.assertFalse(result["ok"])
        self.assertFalse(result["focused"])
        send_ctrl_v.assert_not_called()

    def test_send_failure_reports_clear_error(self):
        with patch.object(scrcpy, "_windows_find_window", return_value=123), \
             patch.object(scrcpy, "_windows_focus_hwnd", return_value=True), \
             patch.object(scrcpy, "_windows_send_ctrl_v", return_value=False):
            result = scrcpy._paste_clipboard_windows("RemoteHP-Mirror: HP", 0)

        self.assertFalse(result["ok"])
        self.assertTrue(result["focused"])
        self.assertFalse(result["pasted"])
        self.assertIn("Ctrl+V", result["error"])


if __name__ == "__main__":
    unittest.main()
