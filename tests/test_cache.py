import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main as pix_main
from core.thumb_cache import ThumbCache, format_clear_message
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

    def test_help_overlay_documents_purge_cache_shortcut(self):
        self.assertIn("│  c / C     purge thumbnail cache │", HELP_TEXT)

    def test_format_clear_message_handles_singular(self):
        self.assertEqual("Cleared 1 cached thumbnail.", format_clear_message(1))

    def test_format_clear_message_includes_location(self):
        location = Path.home() / "photos"
        self.assertEqual(
            "Cleared 2 cached thumbnails for ~/photos.",
            format_clear_message(2, location),
        )


if __name__ == "__main__":
    unittest.main()
