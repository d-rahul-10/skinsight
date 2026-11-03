from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from ml.dataset import LABEL_COLUMN, SkinImageDataset, load_manifest
from ml.metrics import classification_metrics
from ml.model import build_classifier
from ml.preprocess import build_transform


def evaluate(csv_path: str, weights_path: str, data_root: str | None = None, batch_size: int = 16) -> dict[str, object]:
    artifact = Path(weights_path).expanduser().resolve()
    metadata = json.loads(artifact.with_suffix(".classes.json").read_text(encoding="utf-8"))
    classes = metadata["classes"]
    mapping = {name: index for index, name in enumerate(classes)}
    frame = load_manifest(csv_path, data_root=data_root)
    dataset = SkinImageDataset(frame, mapping, build_transform(training=False))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_classifier(metadata["architecture"], len(classes), pretrained=False).to(device)
    checkpoint = torch.load(artifact, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint.get("state_dict", checkpoint), strict=True)
    model.eval()
    truth: list[int] = []
    pred: list[int] = []
    with torch.no_grad():
        for images, labels in loader:
            logits = model(images.to(device))
            truth.extend(labels.tolist())
            pred.extend(logits.argmax(1).cpu().tolist())
    result = {"metrics": classification_metrics(truth, pred, len(classes)), "classes": classes,
              "sample_count": len(dataset), "model_version": metadata.get("model_version")}
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a trained model bundle on an independent labelled CSV.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--weights", default="models/efficientnet_b0.pth")
    parser.add_argument("--data-root")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    evaluate(args.csv, args.weights, args.data_root, args.batch_size)
