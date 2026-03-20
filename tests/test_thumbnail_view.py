import unittest

from views.thumbnail_view import _scroll_fraction_for_item


class ThumbnailViewTests(unittest.TestCase):
    def test_scroll_fraction_stays_at_top_when_content_fits_viewport(self):
        self.assertEqual(
            0.0,
            _scroll_fraction_for_item(
                target_y=0,
                item_height=194,
                content_height=194,
                viewport_height=900,
                current_top=500,
                current_bottom=1400,
            ),
        )

    def test_scroll_fraction_stays_put_when_item_is_already_visible(self):
        self.assertIsNone(
            _scroll_fraction_for_item(
                target_y=194,
                item_height=194,
                content_height=2000,
                viewport_height=600,
                current_top=0,
                current_bottom=600,
            )
        )

    def test_scroll_fraction_moves_down_when_item_falls_below_viewport(self):
        self.assertEqual(
            (388 + 194 - 300) / 1000,
            _scroll_fraction_for_item(
                target_y=388,
                item_height=194,
                content_height=1000,
                viewport_height=300,
                current_top=0,
                current_bottom=300,
            ),
        )


if __name__ == "__main__":
    unittest.main()
