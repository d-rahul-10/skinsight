# Dataset preparation guide

SkinSight never automatically downloads datasets. Obtain a named dataset from its official source, comply with its licence and preserve the source documentation. Store the dataset outside the repository when practical.

## Manifest schema

A UTF-8 CSV requires:

| Column | Required | Meaning |
|---|---|---|
| `image` | Yes | Absolute image path or path relative to `--data-root` (defaults to CSV parent). |
| `label` | Yes | Dataset-defined target label, non-empty. |
| `patient_id` | Recommended | Source patient grouping ID, where available. Never invent this field. |

Example (illustrative rows only, not present training data):

```csv
image,label,patient_id
images/ISIC_0000000.jpg,nv,patient_001
images/ISIC_0000001.jpg,mel,patient_002
```

The CSV loader validates columns, nonblank labels, and existence of every image file. Labels are converted to trimmed strings. The training pipeline sorts observed labels to define the class order and saves that exact order with the checkpoint.

## Dataset handling

For datasets arranged in one directory per class, `build_manifest.py` can create the required CSV. It uses each immediate subdirectory as a class and removes common numeric prefixes/count suffixes from folder names. It does not infer patient IDs or merge distinct class folders. Review the generated labels before training.

For HAM10000, use its documented diagnosis labels such as `akiec`, `bcc`, `bkl`, `df`, `mel`, `nv`, and `vasc`; map metadata image IDs to downloaded image files. Use patient-level grouping only where the dataset provides a valid patient identifier. Do not assume lesion ID and patient ID have identical semantics. For ISIC, select and document a specific challenge/archive edition and exact target field. Do not combine editions or infer labels from image names.

When patient IDs exist, `split_manifest` attempts `StratifiedGroupKFold` and verifies that groups do not overlap; for sparse groups, group-safe random splits are used. Without patient IDs, stratified splits are attempted where class counts are adequate and plain random splitting is a fallback. Always inspect split sizes and class counts, particularly in tiny/imbalanced datasets.

The training script applies inverse-frequency class weights and only augments its training transform. Use official data splits if the challenge requires them; do not evaluate on training or validation rows and describe that as a held-out test. `ml/evaluate.py` accepts a separately supplied labelled CSV and reports test metrics.

## Domain limitations

HAM10000/ISIC datasets often contain dermoscopic clinical/research imagery. Those sources do not guarantee generalization to ordinary smartphone photos, different cameras, lighting, skin tones, or clinical settings. Dataset accuracy is not clinical validation. This prototype is not for diagnosis or care decisions.
