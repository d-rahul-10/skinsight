from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def assess_image_quality(
    image: Image.Image,
    *,
    min_dimension: int = 128,
    blur_threshold: float = 35.0,
    dark_threshold: float = 35.0,
    bright_threshold: float = 220.0,
) -> dict[str, object]:
    """Apply transparent image heuristics; this does not determine lesion presence."""
    rgb = image.convert("RGB")
    pixels = np.asarray(rgb)
    height, width = pixels.shape[:2]
    gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_brightness = float(pixels.mean())
    warnings: list[str] = []
    reasons: list[str] = []

    if min(width, height) < min_dimension:
        reasons.append(f"The shorter image dimension is below the {min_dimension}px minimum heuristic.")
    if laplacian_variance < blur_threshold:
        warnings.append("The image may be blurred or lack fine detail (Laplacian-variance heuristic).")
    if mean_brightness < dark_threshold:
        warnings.append("The image appears unusually dark based on average brightness.")
    elif mean_brightness > bright_threshold:
        warnings.append("The image appears unusually bright based on average brightness.")

    unsuitable = bool(reasons)
    status = "unsuitable" if unsuitable else ("warning" if warnings else "good")
    return {
        "status": status,
        "suitable": not unsuitable,
        "warnings": warnings,
        "reasons": reasons,
        "metrics": {
            "width": int(width),
            "height": int(height),
            "laplacian_variance": round(laplacian_variance, 2),
            "mean_brightness": round(mean_brightness, 2),
            "minimum_dimension_heuristic": int(min_dimension),
        },
    }
