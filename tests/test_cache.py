import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main as pix_main
from core.thumb_cache import ThumbCache, format_clear_message, format_wipe_all_message
from overlays.help_overlay import HELP_TEXT


class CacheTests(unittest.TestCase):
    def test_clear_removes_matching_cached_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            photos_dir = Path(tmpdir) / "photos"
            photos_dir.mkdir()
            image_a = photos_dir / "a.jpg"
            image_b = photos_dir / "b.png"
            image_a.write_bytes(b"a")
            image_b.write_bytes(b"b")

            cache = ThumbCache(photos_dir)
            cache.cache_dir = Path(tmpdir) / "cache"
            cache.cache_dir.mkdir()

            cache.get_cache_path(image_a).write_bytes(b"thumb-a")
            cache.get_cache_path(image_b).write_bytes(b"thumb-b")

            removed = cache.clear(recursive=False)

            self.assertEqual(2, removed)
            self.assertEqual([], list(cache.cache_dir.iterdir()))

    def test_clear_honors_recursive_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            photos_dir = Path(tmpdir) / "photos"
            nested_dir = photos_dir / "nested"
            nested_dir.mkdir(parents=True)
            root_image = photos_dir / "root.jpg"
            nested_image = nested_dir / "nested.jpg"
            root_image.write_bytes(b"root")
            nested_image.write_bytes(b"nested")

            cache = ThumbCache(photos_dir)
            cache.cache_dir = Path(tmpdir) / "cache"
            cache.cache_dir.mkdir()

            root_cache = cache.get_cache_path(root_image)
            nested_cache = cache.get_cache_path(nested_image)
            root_cache.write_bytes(b"thumb-root")
            nested_cache.write_bytes(b"thumb-nested")

            removed = cache.clear(recursive=False)

            self.assertEqual(1, removed)
            self.assertFalse(root_cache.exists())
            self.assertTrue(nested_cache.exists())

    def test_wipe_all_recreates_cache_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ThumbCache(Path(tmpdir))
            cache.cache_dir = Path(tmpdir) / "cache"
            cache.cache_dir.mkdir()
            (cache.cache_dir / "thumb.webp").write_bytes(b"thumb")

            cache.wipe_all()

            self.assertTrue(cache.cache_dir.exists())
            self.assertEqual([], list(cache.cache_dir.iterdir()))

    def test_wipe_all_falls_back_to_in_place_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            photos_dir = Path(tmpdir) / "photos"
            photos_dir.mkdir()
            cache = ThumbCache(photos_dir)
            cache.cache_dir = Path(tmpdir) / "cache"
            cache.cache_dir.mkdir()
            (cache.cache_dir / "thumb.webp").write_bytes(b"thumb")

            with mock.patch("pathlib.Path.replace", side_effect=OSError("busy")):
                cache.wipe_all()

            self.assertTrue(cache.cache_dir.exists())
            self.assertEqual([], list(cache.cache_dir.iterdir()))

    @mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_cli_clear_cache_prints_result(self, stdout):
        with tempfile.TemporaryDirectory() as tmpdir:
            photos_dir = Path(tmpdir) / "photos"
            photos_dir.mkdir()

            with mock.patch("main.ThumbCache.clear", return_value=3):
                with mock.patch("sys.argv", ["pix", "--clear-cache", str(photos_dir)]):
                    with self.assertRaises(SystemExit) as exit_info:
                        pix_main.main()

        self.assertEqual(0, exit_info.exception.code)
        self.assertIn("Cleared 3 cached thumbnails for", stdout.getvalue())
        self.assertIn("(cache: ~/.cache/pix).", stdout.getvalue())

    def test_help_overlay_documents_purge_cache_shortcut(self):
        self.assertIn("│  c / C     purge thumbnail cache │", HELP_TEXT)

    def test_help_overlay_documents_purge_entire_cache_shortcut(self):
        self.assertIn("│  x         purge entire cache    │", HELP_TEXT)

    def test_help_overlay_documents_multi_select_shortcuts(self):
        self.assertIn("│  A         select all            │", HELP_TEXT)
        self.assertIn("│  U         deselect all          │", HELP_TEXT)

    def test_format_clear_message_handles_singular(self):
        self.assertEqual("Cleared 1 cached thumbnail.", format_clear_message(1))

    def test_format_clear_message_includes_location(self):
        location = Path.home() / "photos"
        self.assertEqual(
            "Cleared 2 cached thumbnails for ~/photos (cache: ~/.cache/pix).",
            format_clear_message(2, location, Path.home() / ".cache" / "pix"),
        )

    def test_format_wipe_all_message_includes_cache_dir(self):
        self.assertEqual(
            "Cleared entire thumbnail cache (cache: ~/.cache/pix).",
            format_wipe_all_message(Path.home() / ".cache" / "pix"),
        )


if __name__ == "__main__":
    unittest.main()
