import unittest
import plistlib
from pathlib import Path
import tempfile
from unittest import mock
import io

import main as pix_main
from core import macos_wallpaper, wallpaper
from overlays.help_overlay import HELP_TEXT


class WallpaperTests(unittest.TestCase):
    DEMO_URI = Path("/tmp/demo.jpg").resolve().as_uri()

    def test_missing_file_returns_error(self):
        success, message = wallpaper.set_wallpaper(Path("/tmp/pix-missing-file.jpg"))
        self.assertFalse(success)
        self.assertIn("File not found", message)

    @mock.patch("core.wallpaper.sys.platform", "linux")
    def test_non_macos_reports_unsupported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "demo.jpg"
            image_path.write_bytes(b"demo")

            success, message = wallpaper.set_wallpaper(image_path)

        self.assertFalse(success)
        self.assertIn("only supported on macOS", message)

    @mock.patch("core.wallpaper._set_wallpaper_macos_applescript")
    @mock.patch("core.wallpaper._set_wallpaper_macos_store")
    def test_macos_prefers_store_backend(self, mock_store, mock_applescript):
        mock_store.return_value = (True, "Wallpaper updated: demo.jpg")

        success, message = wallpaper._set_wallpaper_macos(Path("/tmp/demo.jpg"))

        self.assertTrue(success)
        self.assertEqual("Wallpaper updated: demo.jpg", message)
        mock_applescript.assert_not_called()

    @mock.patch("core.wallpaper._set_wallpaper_macos_applescript")
    @mock.patch("core.wallpaper._set_wallpaper_macos_store")
    def test_macos_falls_back_to_applescript(self, mock_store, mock_applescript):
        mock_store.return_value = (False, "Store failed")
        mock_applescript.return_value = (True, "Wallpaper set: demo.jpg")

        success, message = wallpaper._set_wallpaper_macos(Path("/tmp/demo.jpg"))

        self.assertTrue(success)
        self.assertEqual("Wallpaper set: demo.jpg", message)
        mock_applescript.assert_called_once()

    def test_tahoe_store_updates_desktop_configuration(self):
        store = {
            "Spaces": {
                "abc": {
                    "Default": {
                        "Desktop": {
                            "Content": {
                                "Choices": [],
                                "EncodedOptionValues": b"keep-me",
                                "Shuffle": "$null",
                            }
                        }
                    }
                }
            }
        }

        updated = macos_wallpaper._rewrite_store(store, Path("/tmp/demo.jpg"))

        self.assertEqual(1, updated)
        desktop = store["Spaces"]["abc"]["Default"]["Desktop"]
        self.assertEqual("$null", desktop["Content"]["Shuffle"])
        self.assertEqual(b"keep-me", desktop["Content"]["EncodedOptionValues"])
        choice = desktop["Content"]["Choices"][0]
        self.assertEqual("com.apple.wallpaper.choice.image", choice["Provider"])
        config = plistlib.loads(choice["Configuration"])
        self.assertEqual("imageFile", config["type"])
        self.assertEqual(self.DEMO_URI, config["url"]["relative"])
        self.assertIn("LastSet", desktop)
        self.assertIn("LastUse", desktop)

    def test_tahoe_store_write_round_trip(self):
        initial = {
            "SystemDefault": {
                "Desktop": {
                    "Content": {
                        "Choices": [],
                        "EncodedOptionValues": "$null",
                        "Shuffle": "$null",
                    }
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "Index.plist"
            with store_path.open("wb") as handle:
                plistlib.dump(initial, handle, fmt=plistlib.FMT_BINARY)

            with mock.patch("core.macos_wallpaper._restart_wallpaper_agent"):
                success, message = macos_wallpaper.set_wallpaper(Path("/tmp/demo.jpg"), store_path=store_path)

            self.assertTrue(success)
            self.assertEqual("Wallpaper updated: demo.jpg", message)

            with store_path.open("rb") as handle:
                stored = plistlib.load(handle)

        choice = stored["SystemDefault"]["Desktop"]["Content"]["Choices"][0]
        config = plistlib.loads(choice["Configuration"])
        self.assertEqual(self.DEMO_URI, config["url"]["relative"])

    def test_tahoe_store_missing_path_reports_error(self):
        success, message = macos_wallpaper.set_wallpaper(Path("/tmp/demo.jpg"), store_path=Path("/tmp/does-not-exist.plist"))
        self.assertFalse(success)
        self.assertIn("Wallpaper store not found", message)

    def test_tahoe_store_reports_missing_desktop_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "Index.plist"
            with store_path.open("wb") as handle:
                plistlib.dump({"Idle": {}}, handle, fmt=plistlib.FMT_BINARY)

            with mock.patch("core.macos_wallpaper._restart_wallpaper_agent"):
                success, message = macos_wallpaper.set_wallpaper(Path("/tmp/demo.jpg"), store_path=store_path)

        self.assertFalse(success)
        self.assertIn("did not contain any desktop entries", message)

    def test_image_choice_configuration_is_binary_plist(self):
        choice = macos_wallpaper._image_choice(Path("/tmp/demo.jpg"))
        config = plistlib.loads(choice["Configuration"])
        self.assertEqual("imageFile", config["type"])
        self.assertEqual(self.DEMO_URI, config["url"]["relative"])

    def test_help_overlay_documents_b_shortcut(self):
        self.assertIn("│  b         set as wallpaper      │", HELP_TEXT)
        self.assertNotIn("b, W", HELP_TEXT)

    @mock.patch("core.macos_wallpaper.set_wallpaper", return_value=(True, "Wallpaper updated: demo.jpg"))
    def test_wallpaper_backend_import_wrapper(self, _mock_backend):
        success, message = wallpaper._set_wallpaper_macos_store(Path("/tmp/demo.jpg"))
        self.assertTrue(success)
        self.assertEqual("Wallpaper updated: demo.jpg", message)

    def test_extract_wallpaper_agent_pid(self):
        output = "state = running\npid = 12345\njob state = running\n"
        self.assertEqual(12345, macos_wallpaper._extract_wallpaper_agent_pid(output))

    def test_extract_wallpaper_agent_pid_missing(self):
        self.assertIsNone(macos_wallpaper._extract_wallpaper_agent_pid("state = running\n"))

    @mock.patch("core.macos_wallpaper.time.sleep", return_value=None)
    @mock.patch("core.macos_wallpaper._get_wallpaper_agent_pid", side_effect=[111, 111, 222])
    @mock.patch("core.macos_wallpaper.subprocess.run")
    def test_restart_wallpaper_agent_waits_for_new_pid(self, mock_run, _mock_pid, _mock_sleep):
        mock_run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        macos_wallpaper._restart_wallpaper_agent(timeout_s=0.5)
        mock_run.assert_called_once_with(
            ["/bin/kill", "111"],
            capture_output=True,
            text=True,
            check=False,
        )

    @mock.patch("core.macos_wallpaper._restart_wallpaper_agent", side_effect=RuntimeError("no refresh"))
    def test_set_wallpaper_reports_refresh_failure(self, _mock_restart):
        initial = {
            "SystemDefault": {
                "Desktop": {
                    "Content": {
                        "Choices": [],
                        "EncodedOptionValues": "$null",
                        "Shuffle": "$null",
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "Index.plist"
            with store_path.open("wb") as handle:
                plistlib.dump(initial, handle, fmt=plistlib.FMT_BINARY)

            success, message = macos_wallpaper.set_wallpaper(Path("/tmp/demo.jpg"), store_path=store_path)

        self.assertFalse(success)
        self.assertIn("agent refresh failed", message)

    @mock.patch("main.set_wallpaper", return_value=(True, "Wallpaper updated: demo.jpg"))
    @mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_cli_set_wallpaper_exits_successfully(self, stdout, mock_set_wallpaper):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "demo.jpg"
            image_path.write_bytes(b"demo")

            with mock.patch("sys.argv", ["pix", "--set-wallpaper", str(image_path)]):
                with self.assertRaises(SystemExit) as exit_info:
                    pix_main.main()

        self.assertEqual(0, exit_info.exception.code)
        mock_set_wallpaper.assert_called_once()
        self.assertIn("Wallpaper updated: demo.jpg", stdout.getvalue())

    @mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_cli_set_wallpaper_rejects_directories(self, stdout):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("sys.argv", ["pix", "--set-wallpaper", tmpdir]):
                with self.assertRaises(SystemExit) as exit_info:
                    pix_main.main()

        self.assertEqual(1, exit_info.exception.code)
        self.assertIn("--set-wallpaper requires a single image file path", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
