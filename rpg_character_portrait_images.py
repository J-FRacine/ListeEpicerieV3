"""Traitement d'image pour le portrait d'un personnage JDR.

Le module est indépendant de NiceGUI et de PostgreSQL.
"""
from __future__ import annotations

import base64
import inspect
from io import BytesIO
from pathlib import PurePath
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_BYTES = 8_000_000
MAX_PIXELS = 25_000_000
MAX_DIMENSION = 1000
JPEG_QUALITY = 86
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def _safe_file_name(value: Any) -> str | None:
    name = str(value or "").strip()
    if not name:
        return None
    name = PurePath(name.replace("\\", "/")).name.strip()
    return name[:255] or None


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    has_alpha = (
        image.mode in {"RGBA", "LA"}
        or (image.mode == "P" and "transparency" in image.info)
    )
    if has_alpha:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def normalize_portrait(
    data: bytes,
    *,
    content_type: str | None = None,
    file_name: str | None = None,
) -> dict[str, Any]:
    """Valide, redimensionne et réencode un portrait en JPEG."""
    del content_type  # Le vrai format est détecté à partir du fichier.

    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError("La photo reçue est invalide.")

    raw = bytes(data)
    if not raw:
        raise ValueError("La photo est vide.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError(
            "La photo est trop volumineuse. "
            "Choisissez une image de 8 Mo ou moins."
        )

    try:
        with Image.open(BytesIO(raw)) as opened:
            detected_format = str(opened.format or "").upper()
            if detected_format not in ALLOWED_FORMATS:
                raise ValueError(
                    "Format non pris en charge. "
                    "Utilisez une image JPEG, PNG ou WEBP."
                )

            frames = int(getattr(opened, "n_frames", 1) or 1)
            if frames != 1:
                raise ValueError(
                    "Les images animées ne sont pas prises en charge."
                )

            width, height = opened.size
            if width <= 0 or height <= 0:
                raise ValueError("Les dimensions de la photo sont invalides.")
            if width * height > MAX_PIXELS:
                raise ValueError(
                    "La photo contient trop de pixels. "
                    "Utilisez une image de 25 mégapixels ou moins."
                )

            opened.load()
            image = ImageOps.exif_transpose(opened)
            image = _flatten_to_rgb(image)

            try:
                resampling = Image.Resampling.LANCZOS
            except AttributeError:
                resampling = Image.LANCZOS

            image.thumbnail(
                (MAX_DIMENSION, MAX_DIMENSION),
                resampling,
            )

            output = BytesIO()
            image.save(
                output,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
            )
            encoded = output.getvalue()
            final_width, final_height = image.size

    except ValueError:
        raise
    except UnidentifiedImageError as error:
        raise ValueError(
            "Le fichier choisi n’est pas une image JPEG, PNG ou WEBP valide."
        ) from error
    except OSError as error:
        raise ValueError(
            "La photo n’a pas pu être lue. "
            "Essayez une autre image JPEG, PNG ou WEBP."
        ) from error

    return {
        "image_data": encoded,
        "mime_type": "image/jpeg",
        "width": int(final_width),
        "height": int(final_height),
        "image_size": len(encoded),
        "file_name": _safe_file_name(file_name),
    }


def portrait_to_data_url(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None

    data = row.get("image_data")
    if data is None:
        return None
    if isinstance(data, memoryview):
        data = data.tobytes()
    elif isinstance(data, bytearray):
        data = bytes(data)

    if not isinstance(data, bytes) or not data:
        return None

    mime_type = str(
        row.get("mime_type") or "image/jpeg"
    ).strip() or "image/jpeg"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


async def _read_result(value: Any) -> bytes:
    if inspect.isawaitable(value):
        value = await value
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, bytes):
        return value
    raise ValueError("Le contenu du fichier téléversé est invalide.")


async def read_upload_event(event: Any) -> dict[str, Any]:
    """Lit NiceGUI 3.x et conserve une compatibilité avec l'ancien événement."""
    current_file = getattr(event, "file", None)
    if current_file is not None:
        reader = getattr(current_file, "read", None)
        if not callable(reader):
            raise ValueError("Le fichier téléversé ne peut pas être lu.")
        data = await _read_result(reader())
        return {
            "data": data,
            "file_name": _safe_file_name(
                getattr(current_file, "name", None)
            ),
            "content_type": str(
                getattr(current_file, "content_type", "") or ""
            ),
        }

    legacy_content = getattr(event, "content", None)
    reader = getattr(legacy_content, "read", None)
    if not callable(reader):
        raise ValueError("Le fichier téléversé ne peut pas être lu.")

    data = await _read_result(reader())
    return {
        "data": data,
        "file_name": _safe_file_name(getattr(event, "name", None)),
        "content_type": str(
            getattr(event, "content_type", None)
            or getattr(event, "type", None)
            or ""
        ),
    }
