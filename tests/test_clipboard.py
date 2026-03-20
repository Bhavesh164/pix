import unittest
from pathlib import Path
from unittest import mock

from core import clipboard
from overlays.help_overlay import HELP_TEXT


class ClipboardTests(unittest.TestCase):
    def test_copy_paths_requires_at_least_one_path(self):
        success, message = clipboard.copy_paths([])
        self.assertFalse(success)
        self.assertEqual("No images selected to copy.", message)

    @mock.patch("core.clipboard._copy_paths_as_text")
    @mock.patch("core.clipboard._copy_paths_macos", return_value=(True, ""))
    @mock.patch("core.clipboard.sys.platform", "darwin")
    def test_copy_paths_prefers_native_macos_copy(self, mock_native_copy, mock_text_copy):
        success, message = clipboard.copy_paths([Path("/tmp/a.jpg")], clipboard_owner=object())

        self.assertTrue(success)
        self.assertEqual("Copied 1 image to clipboard.", message)
        mock_native_copy.assert_called_once()
        mock_text_copy.assert_not_called()

    @mock.patch("core.clipboard._copy_paths_as_text", return_value=(True, ""))
    @mock.patch("core.clipboard._copy_paths_macos", return_value=(False, "native clipboard unavailable"))
    @mock.patch("core.clipboard.sys.platform", "darwin")
    def test_copy_paths_falls_back_to_text_when_native_copy_fails(self, mock_native_copy, mock_text_copy):
        success, message = clipboard.copy_paths(
            [Path("/tmp/a.jpg"), Path("/tmp/b.jpg")],
            clipboard_owner=object(),
        )

        self.assertTrue(success)
        self.assertEqual("Copied 2 image paths to clipboard.", message)
        mock_native_copy.assert_called_once()
        mock_text_copy.assert_called_once()

    def test_format_copy_message_handles_plural_paths(self):
        self.assertEqual(
            "Copied 2 image paths to clipboard.",
            clipboard.format_copy_message(2, copied_as_paths=True),
        )

    def test_help_overlay_documents_copy_shortcut(self):
        self.assertIn("│  y         copy selected         │", HELP_TEXT)


if __name__ == "__main__":
    unittest.main()
