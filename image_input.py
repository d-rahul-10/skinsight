from __future__ import annotations

import warnings
from io import BytesIO
from pathlib import PurePath

from PIL import Image, UnidentifiedImageError


ALLOWED_EXTENSIONS = {".jpg": "JPEG", ".jpeg": "JPEG", ".jpe": "JPEG", ".png": "PNG", ".webp": "WEBP"}
FORMAT_CONTENT_TYPES = {
    "JPEG": {"image/jpeg", "image/jpg"},
    "PNG": {"image/png"},
    "WEBP": {"image/webp"},
}


class ImageInputError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def decode_uploaded_image(
    filename: str | None,
    content_type: str | None,
    payload: bytes,
    *,
    max_bytes: int,
    max_dimension: int,
) -> Image.Image:
    if not filename or PurePath(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ImageInputError("Unsupported image format. Upload a JPG, JPEG, PNG, or WEBP image.")
    if not payload:
        raise ImageInputError("The uploaded image is empty.")
    if len(payload) > max_bytes:
        raise ImageInputError(f"The image exceeds the {max_bytes // (1024 * 1024)} MB upload limit.", 413)

    expected_format = ALLOWED_EXTENSIONS[PurePath(filename).suffix.lower()]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as probe:
                actual_format = probe.format
                width, height = probe.size
                probe.verify()
            if actual_format != expected_format:
                raise ImageInputError("The file extension does not match the image content.")
            if content_type and content_type.lower().split(";")[0] not in FORMAT_CONTENT_TYPES[expected_format]:
                raise ImageInputError("The uploaded content type does not match the image format.")
            if width > max_dimension or height > max_dimension:
                raise ImageInputError(f"Image dimensions must not exceed {max_dimension}px on either side.", 413)
            with Image.open(BytesIO(payload)) as decoded:
                decoded.load()
                return decoded.convert("RGB")
    except ImageInputError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageInputError("The uploaded file is not a valid, readable image.") from exc
