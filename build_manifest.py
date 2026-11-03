from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def class_label_from_directory(name: str) -> str:
    label = re.sub(r"^\d+\.\s*", "", name)
    label = re.sub(r"\s+-\s+\d+(?:\.\d+)?\s*[kK]?$", "", label)
    label = re.sub(r"\s+\d+(?:\.\d+)?\s*[kK]?$", "", label)
    return label.strip()


def build_manifest(data_root: Path, output: Path) -> dict[str, int]:
    root = data_root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Dataset directory was not found: {root}")

    rows: list[tuple[str, str]] = []
    counts: Counter[str] = Counter()
    for class_directory in sorted(path for path in root.iterdir() if path.is_dir()):
        label = class_label_from_directory(class_directory.name)
        if not label:
            raise ValueError(f"Could not derive a class label from directory: {class_directory.name}")
        images = sorted(
            path.resolve()
            for path in class_directory.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
        rows.extend((str(image), label) for image in images)
        counts[label] += len(images)

    if not rows or len(counts) < 2:
        raise ValueError("Dataset must contain images in at least two class directories.")

    destination = output.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as manifest:
        writer = csv.writer(manifest)
        writer.writerow(("image", "label"))
        writer.writerows(rows)
    return dict(sorted(counts.items()))


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an image,label CSV from class-named image folders.")
    parser.add_argument("--data-root", required=True, type=Path, help="Directory containing one subdirectory per class")
    parser.add_argument("--output", required=True, type=Path, help="Output CSV manifest path")
    return parser


if __name__ == "__main__":
    args = make_parser().parse_args()
    class_counts = build_manifest(args.data_root, args.output)
    print(f"Wrote {sum(class_counts.values())} images to {args.output}")
    for label, count in class_counts.items():
        print(f"{label}: {count}")
