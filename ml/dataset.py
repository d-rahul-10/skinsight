from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold, train_test_split
from torch.utils.data import Dataset


IMAGE_COLUMN = "image"
LABEL_COLUMN = "label"
PATIENT_COLUMN = "patient_id"


def load_manifest(
    csv_path: str | Path,
    *,
    data_root: str | Path | None = None,
    image_column: str = IMAGE_COLUMN,
    label_column: str = LABEL_COLUMN,
    patient_column: str = PATIENT_COLUMN,
) -> pd.DataFrame:
    manifest_path = Path(csv_path).expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest CSV was not found: {manifest_path}")
    frame = pd.read_csv(manifest_path)
    missing_columns = [column for column in (image_column, label_column) if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"CSV is missing required column(s): {', '.join(missing_columns)}")
    if frame.empty:
        raise ValueError("Manifest CSV contains no rows.")

    root = Path(data_root).expanduser().resolve() if data_root else manifest_path.parent
    bad_labels = frame[label_column].isna() | frame[label_column].astype(str).str.strip().eq("")
    bad_images = frame[image_column].isna() | frame[image_column].astype(str).str.strip().eq("")
    if bad_labels.any() or bad_images.any():
        raise ValueError(f"Invalid manifest rows: {int((bad_labels | bad_images).sum())} have an empty image path or label.")

    resolved: list[str] = []
    missing: list[str] = []
    for value in frame[image_column].astype(str):
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        if not candidate.is_file():
            missing.append(value)
        resolved.append(str(candidate))
    if missing:
        examples = ", ".join(missing[:5])
        suffix = "…" if len(missing) > 5 else ""
        raise FileNotFoundError(f"{len(missing)} image file(s) referenced by the CSV are missing: {examples}{suffix}")

    frame = frame.copy()
    frame[label_column] = frame[label_column].astype(str).str.strip()
    frame["_resolved_image_path"] = resolved
    if patient_column in frame.columns:
        frame[patient_column] = frame[patient_column].fillna("").astype(str).str.strip()
    return frame


def _stratification_is_suitable(labels: pd.Series, n_splits: int) -> bool:
    counts = labels.value_counts()
    return len(counts) >= 2 and int(counts.min()) >= n_splits


def split_manifest(
    frame: pd.DataFrame,
    *,
    label_column: str = LABEL_COLUMN,
    patient_column: str = PATIENT_COLUMN,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """Split without patient overlap when IDs exist; otherwise stratify when class counts allow."""
    labels = frame[label_column].astype(str)
    has_patient_ids = patient_column in frame.columns and frame[patient_column].astype(str).str.strip().ne("").any()
    if has_patient_ids:
        groups = frame[patient_column].astype(str).str.strip().copy()
        missing_group = groups.eq("")
        groups.loc[missing_group] = [f"__row_{idx}" for idx in frame.index[missing_group]]
        unique_groups = groups.nunique()
        if unique_groups >= 5:
            try:
                first_splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
                remaining_idx, test_idx = next(first_splitter.split(frame, labels, groups))
                remaining = frame.iloc[remaining_idx].copy()
                remaining_labels = remaining[label_column].astype(str)
                remaining_groups = groups.iloc[remaining_idx]
                val_splits = min(8, remaining_groups.nunique())
                if val_splits >= 2:
                    second_splitter = StratifiedGroupKFold(
                        n_splits=val_splits, shuffle=True, random_state=seed + 1
                    )
                    train_local, val_local = next(
                        second_splitter.split(remaining, remaining_labels, remaining_groups)
                    )
                    result = {
                        "train": remaining.iloc[train_local].copy(),
                        "validation": remaining.iloc[val_local].copy(),
                        "test": frame.iloc[test_idx].copy(),
                    }
                    _assert_no_group_leakage(result, groups, patient_column)
                    return result
            except ValueError:
                pass
        warnings.warn("Patient IDs are present but too sparse for stratified group folds; using group-safe random splits.", RuntimeWarning)
        first = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
        remaining_idx, test_idx = next(first.split(frame, labels, groups))
        remaining = frame.iloc[remaining_idx].copy()
        second = GroupShuffleSplit(n_splits=1, test_size=0.125, random_state=seed + 1)
        train_local, val_local = next(
            second.split(remaining, remaining[label_column], groups.iloc[remaining_idx])
        )
        result = {
            "train": remaining.iloc[train_local].copy(),
            "validation": remaining.iloc[val_local].copy(),
            "test": frame.iloc[test_idx].copy(),
        }
        _assert_no_group_leakage(result, groups, patient_column)
        return result

    indices = frame.index.to_numpy()
    stratify = labels if _stratification_is_suitable(labels, 2) else None
    try:
        train_val_idx, test_idx = train_test_split(
            indices, test_size=0.2, random_state=seed, stratify=stratify
        )
    except ValueError:
        train_val_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=seed)
    train_val = frame.loc[train_val_idx].copy()
    train_val_labels = train_val[label_column].astype(str)
    stratify_val = train_val_labels if _stratification_is_suitable(train_val_labels, 2) else None
    try:
        train_idx, val_idx = train_test_split(
            train_val.index.to_numpy(), test_size=0.125, random_state=seed + 1, stratify=stratify_val
        )
    except ValueError:
        train_idx, val_idx = train_test_split(
            train_val.index.to_numpy(), test_size=0.125, random_state=seed + 1
        )
    return {
        "train": frame.loc[train_idx].copy(),
        "validation": frame.loc[val_idx].copy(),
        "test": frame.loc[test_idx].copy(),
    }


def _assert_no_group_leakage(
    splits: dict[str, pd.DataFrame], original_groups: pd.Series, patient_column: str
) -> None:
    group_sets: dict[str, set[str]] = {}
    for name, subset in splits.items():
        if patient_column in subset.columns:
            group_sets[name] = {str(value).strip() for value in subset[patient_column] if str(value).strip()}
        else:
            group_sets[name] = set()
    names = list(group_sets)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            if group_sets[left] & group_sets[right]:
                raise RuntimeError("Patient-level data leakage detected between generated splits.")


class SkinImageDataset(Dataset):
    def __init__(
        self,
        frame: pd.DataFrame,
        class_to_idx: dict[str, int],
        transform: Any,
        *,
        label_column: str = LABEL_COLUMN,
    ) -> None:
        self.frame = frame.reset_index(drop=True)
        self.class_to_idx = class_to_idx
        self.transform = transform
        self.label_column = label_column
        unknown = sorted(set(self.frame[label_column].astype(str)) - set(class_to_idx))
        if unknown:
            raise ValueError(f"Labels not present in class mapping: {', '.join(unknown)}")

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, index: int):
        row = self.frame.iloc[index]
        image_path = row.get("_resolved_image_path") or row.get("image")
        if not image_path:
            raise ValueError("Dataset row has no resolved image path.")
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        return self.transform(image), self.class_to_idx[str(row[self.label_column])]
