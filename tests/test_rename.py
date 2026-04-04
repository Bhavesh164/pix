import tempfile
import unittest
from pathlib import Path

from app import PixApp


class RenameImageTests(unittest.TestCase):
    def test_rename_image_updates_path_on_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "old.jpg"
            image_path.write_bytes(b"image")

            app = PixApp.__new__(PixApp)
            app.images = [image_path]
            app.is_single_image = False

            success, message, renamed_path = PixApp.rename_image(app, 0, "new.jpg")

            self.assertTrue(success)
            self.assertEqual("Renamed to new.jpg.", message)
            self.assertEqual(Path(tmpdir) / "new.jpg", renamed_path)
            self.assertEqual(renamed_path, app.images[0])
            self.assertFalse(image_path.exists())
            self.assertTrue(renamed_path.exists())

    def test_rename_image_rejects_empty_name(self):
        app = PixApp.__new__(PixApp)
        app.images = [Path("/tmp/example.jpg")]
        app.is_single_image = False

        success, message, renamed_path = PixApp.rename_image(app, 0, "   ")

        self.assertFalse(success)
        self.assertEqual("Filename cannot be empty.", message)
        self.assertEqual(Path("/tmp/example.jpg"), renamed_path)

    def test_rename_image_rejects_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "old.jpg"
            target = Path(tmpdir) / "taken.jpg"
            source.write_bytes(b"source")
            target.write_bytes(b"taken")

            app = PixApp.__new__(PixApp)
            app.images = [source]
            app.is_single_image = False

            success, message, renamed_path = PixApp.rename_image(app, 0, "taken.jpg")

            self.assertFalse(success)
            self.assertEqual("taken.jpg already exists.", message)
            self.assertEqual(source, renamed_path)
            self.assertEqual(source, app.images[0])


if __name__ == "__main__":
    unittest.main()
