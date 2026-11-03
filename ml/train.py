from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from sklearn.utils.class_weight import compute_class_weight
from torch import nn
from torch.utils.data import DataLoader

from ml.dataset import LABEL_COLUMN, SkinImageDataset, load_manifest, split_manifest
from ml.metrics import classification_metrics
from ml.model import build_classifier
from ml.preprocess import build_transform


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _run_epoch(model, loader, criterion, optimizer, device, *, training: bool):
    model.train(training)
    total_loss = 0.0
    targets: list[int] = []
    predictions: list[int] = []
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        if training:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            logits = model(images)
            loss = criterion(logits, labels)
            if training:
                loss.backward()
                optimizer.step()
        total_loss += float(loss.detach().item()) * labels.size(0)
        predictions.extend(logits.argmax(dim=1).detach().cpu().tolist())
        targets.extend(labels.detach().cpu().tolist())
    metrics = classification_metrics(targets, predictions, model.classifier[-1].out_features if hasattr(model, "classifier") and isinstance(model.classifier, nn.Sequential) else len(set(targets)))
    return total_loss / max(len(loader.dataset), 1), metrics


def train(args: argparse.Namespace) -> dict[str, object]:
    set_seed(args.seed)
    manifest = load_manifest(args.csv, data_root=args.data_root)
    splits = split_manifest(manifest, seed=args.seed)
    classes = sorted(manifest[LABEL_COLUMN].astype(str).unique().tolist())
    if len(classes) < 2:
        raise ValueError("Training requires at least two distinct classes.")
    class_to_idx = {name: index for index, name in enumerate(classes)}
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    train_ds = SkinImageDataset(splits["train"], class_to_idx, build_transform(training=True))
    val_ds = SkinImageDataset(splits["validation"], class_to_idx, build_transform(training=False))
    test_ds = SkinImageDataset(splits["test"], class_to_idx, build_transform(training=False))
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)

    model = build_classifier(args.architecture, len(classes), pretrained=args.pretrained).to(device)
    targets = np.asarray(
        [class_to_idx[label] for label in splits["train"][LABEL_COLUMN].astype(str)], dtype=np.int64
    )
    present_classes = np.unique(targets).astype(np.int64)
    weights = np.ones(len(classes), dtype=np.float32)
    present_weights = compute_class_weight(class_weight="balanced", classes=present_classes, y=targets)
    for class_id, class_weight in zip(present_classes.tolist(), present_weights.tolist()):
        weights[int(class_id)] = float(class_weight)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32, device=device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    best_loss = float("inf")
    artifact = Path(args.output).expanduser().resolve()
    artifact.parent.mkdir(parents=True, exist_ok=True)
    mapping_path = artifact.with_suffix(".classes.json")
    history: list[dict[str, object]] = []

    for epoch in range(1, args.epochs + 1):
        train_loss, train_metrics = _run_epoch(model, train_loader, criterion, optimizer, device, training=True)
        val_loss, val_metrics = _run_epoch(model, val_loader, criterion, optimizer, device, training=False)
        row = {"epoch": epoch, "train_loss": train_loss, "train_metrics": train_metrics,
               "validation_loss": val_loss, "validation_metrics": val_metrics}
        history.append(row)
        print(json.dumps(row))
        if val_loss < best_loss:
            best_loss = val_loss
            torch.save({"state_dict": model.state_dict()}, artifact)
            mapping_path.write_text(json.dumps({
                "architecture": args.architecture,
                "classes": classes,
                "model_version": args.model_version,
                "image_size": 224,
                "normalization": "imagenet",
                "seed": args.seed,
            }, indent=2), encoding="utf-8")

    # Evaluate the selected best validation checkpoint on held-out test data exactly once.
    checkpoint = torch.load(artifact, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    test_loss, test_metrics = _run_epoch(model, test_loader, criterion, optimizer, device, training=False)
    report = {"best_validation_loss": best_loss, "test_loss": test_loss, "test_metrics": test_metrics,
              "classes": classes, "split_sizes": {key: len(value) for key, value in splits.items()},
              "device": str(device), "history": history}
    report_path = artifact.with_suffix(".metrics.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"final_test_report": report}, indent=2))
    return report


def make_parser() -> argparse.ArgumentParser:
    defaults = json.loads((Path(__file__).parent / "configs" / "default.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description="Train an academic skin-image classifier from a labelled CSV manifest.")
    parser.add_argument("--csv", required=True, help="CSV with image,label and optional patient_id columns")
    parser.add_argument("--data-root", default=None, help="Base directory for relative paths (defaults to CSV directory)")
    parser.add_argument("--output", default=defaults["output"])
    parser.add_argument("--architecture", choices=["efficientnet_b0", "convnext_tiny"], default=defaults["architecture"])
    parser.add_argument("--epochs", type=int, default=defaults["epochs"])
    parser.add_argument("--batch-size", type=int, default=defaults["batch_size"])
    parser.add_argument("--learning-rate", type=float, default=defaults["learning_rate"])
    parser.add_argument("--weight-decay", type=float, default=defaults["weight_decay"])
    parser.add_argument("--seed", type=int, default=defaults["seed"])
    parser.add_argument("--workers", type=int, default=defaults["workers"], help="Use 0 for straightforward Windows compatibility")
    parser.add_argument("--model-version", default=defaults["model_version"])
    parser.add_argument("--pretrained", action="store_true", default=defaults["pretrained"], help="Use torchvision pretrained weights (may download from torchvision on first use)")
    parser.add_argument("--cpu", action="store_true", default=defaults["cpu"])
    return parser


if __name__ == "__main__":
    train(make_parser().parse_args())
