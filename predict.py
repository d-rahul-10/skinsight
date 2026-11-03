from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from backend.app.core.config import Settings
from backend.app.ml.model_service import ModelService
from backend.app.services.image_quality import assess_image_quality
from ml.preprocess import preprocess_image


def predict(image_path: str) -> dict[str, object]:
    settings = Settings.from_env()
    model = ModelService(settings.model_path, model_version=settings.model_version)
    if not model.available:
        return {"model_available": False, "message": model.message, "prediction": None}
    with Image.open(Path(image_path).expanduser()) as source:
        image = source.convert("RGB")
    quality = assess_image_quality(image, min_dimension=settings.min_image_dimension,
                                   blur_threshold=settings.blur_threshold,
                                   dark_threshold=settings.dark_threshold,
                                   bright_threshold=settings.bright_threshold)
    if not quality["suitable"]:
        return {"model_available": True, "quality": quality, "prediction": None,
                "message": "Image quality is unsuitable for processing; provide a clearer, higher-resolution image."}
    result = model.predict(preprocess_image(image))
    return {"model_available": True, "quality": quality,
            "prediction": {"visual_category": result[0], "confidence": result[1]},
            "probabilities": result[2],
            "warning": "Softmax confidence is not necessarily calibrated diagnostic correctness."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    print(json.dumps(predict(parser.parse_args().image), indent=2))
