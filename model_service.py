from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
from torch import nn

from ml.model import build_classifier


class ModelService:
    def __init__(self, weights_path: Path, *, model_version: str = "unavailable") -> None:
        self.weights_path = weights_path
        self.model_version = model_version
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model: nn.Module | None = None
        self.class_names: list[str] = []
        self.message = "No trained model weights are installed. Add a trained checkpoint to enable inference."
        self.architecture = "efficientnet_b0"
        self._load()

    @property
    def available(self) -> bool:
        return self.model is not None and len(self.class_names) >= 2

    def _load(self) -> None:
        mapping_path = self.weights_path.with_suffix(".classes.json")
        if not self.weights_path.is_file() or not mapping_path.is_file():
            return
        try:
            metadata: dict[str, Any] = json.loads(mapping_path.read_text(encoding="utf-8"))
            classes = metadata.get("classes")
            if not isinstance(classes, list) or len(classes) < 2 or any(not isinstance(x, str) or not x.strip() for x in classes):
                self.message = "The model class mapping is invalid. Retrain and export a compatible model bundle."
                return
            architecture = metadata.get("architecture", "efficientnet_b0")
            if not isinstance(architecture, str):
                raise ValueError("Invalid architecture metadata")
            candidate = build_classifier(architecture, len(classes), pretrained=False)
            checkpoint = torch.load(self.weights_path, map_location=self.device, weights_only=True)
            state = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
            if not isinstance(state, dict):
                raise ValueError("Checkpoint does not contain a state dictionary")
            candidate.load_state_dict(state, strict=True)
            candidate.to(self.device)
            candidate.eval()
            self.model = candidate
            self.class_names = [value.strip() for value in classes]
            self.architecture = architecture
            self.model_version = str(metadata.get("model_version", self.model_version))
            self.message = "A trained model bundle is loaded. Results are experimental and not diagnostic."
        except Exception:
            self.model = None
            self.class_names = []
            self.message = "A trained model bundle could not be loaded. Check its compatibility and retrain if needed."

    def predict(self, tensor: torch.Tensor) -> tuple[str, float, list[dict[str, float | str]], int]:
        if not self.available or self.model is None:
            raise RuntimeError("The trained model is unavailable.")
        input_tensor = tensor.to(self.device)
        with torch.no_grad():
            logits = self.model(input_tensor)
            probabilities = torch.softmax(logits, dim=1)[0]
        if probabilities.numel() != len(self.class_names):
            raise RuntimeError("Loaded model output does not match the configured class mapping.")
        score, index = torch.max(probabilities, dim=0)
        ranked = [
            {"category": self.class_names[i], "probability": float(probabilities[i].item())}
            for i in torch.argsort(probabilities, descending=True).tolist()
        ]
        return self.class_names[int(index.item())], float(score.item()), ranked, int(index.item())
