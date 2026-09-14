from __future__ import annotations

import asyncio
import base64
from io import BytesIO
from types import SimpleNamespace
import unittest

from PIL import Image

from rpg_character_portrait_images import (
    MAX_DIMENSION,
    MAX_UPLOAD_BYTES,
    normalize_portrait,
    portrait_to_data_url,
    read_upload_event,
)


def image_bytes(
    mode="RGB",
    size=(1400, 900),
    color=None,
    fmt="PNG",
):
    if color is None:
        color = (
            (50, 100, 150, 255)
            if "A" in mode
            else (50, 100, 150)
        )
    image = Image.new(mode, size, color)
    output = BytesIO()
    image.save(output, format=fmt)
    return output.getvalue()


class PortraitImageTests(unittest.TestCase):
    def test_large_png_is_normalized_to_jpeg_and_resized(self):
        result = normalize_portrait(
            image_bytes(),
            file_name="../portrait.png",
        )
        self.assertEqual(result["mime_type"], "image/jpeg")
        self.assertEqual(result["file_name"], "portrait.png")
        self.assertLessEqual(result["width"], MAX_DIMENSION)
        self.assertLessEqual(result["height"], MAX_DIMENSION)
        self.assertEqual(
            result["image_size"],
            len(result["image_data"]),
        )
        with Image.open(BytesIO(result["image_data"])) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.mode, "RGB")

    def test_transparent_png_is_flattened_to_rgb(self):
        result = normalize_portrait(
            image_bytes(
                mode="RGBA",
                size=(200, 300),
                color=(255, 0, 0, 80),
            )
        )
        with Image.open(BytesIO(result["image_data"])) as image:
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.size, (200, 300))

    def test_data_url_supports_memoryview(self):
        result = normalize_portrait(
            image_bytes(size=(50, 50))
        )
        url = portrait_to_data_url({
            "mime_type": result["mime_type"],
            "image_data": memoryview(result["image_data"]),
        })
        self.assertTrue(
            url.startswith("data:image/jpeg;base64,")
        )
        self.assertTrue(
            base64.b64decode(url.split(",", 1)[1])
        )

    def test_invalid_image_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_portrait(b"not-an-image")

    def test_oversized_upload_is_rejected_before_decoding(self):
        with self.assertRaises(ValueError):
            normalize_portrait(
                b"x" * (MAX_UPLOAD_BYTES + 1)
            )

    def test_gif_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_portrait(
                image_bytes(size=(20, 20), fmt="GIF")
            )

    def test_reads_current_nicegui_upload_event(self):
        class CurrentFile:
            name = "hero.png"
            content_type = "image/png"

            async def read(self):
                return b"abc"

        result = asyncio.run(
            read_upload_event(
                SimpleNamespace(file=CurrentFile())
            )
        )
        self.assertEqual(result["data"], b"abc")
        self.assertEqual(result["file_name"], "hero.png")
        self.assertEqual(
            result["content_type"],
            "image/png",
        )

    def test_reads_legacy_upload_event(self):
        class LegacyContent:
            def read(self):
                return b"legacy"

        result = asyncio.run(
            read_upload_event(
                SimpleNamespace(
                    content=LegacyContent(),
                    name="old.jpg",
                    type="image/jpeg",
                )
            )
        )
        self.assertEqual(result["data"], b"legacy")
        self.assertEqual(result["file_name"], "old.jpg")
        self.assertEqual(
            result["content_type"],
            "image/jpeg",
        )


if __name__ == "__main__":
    unittest.main()
