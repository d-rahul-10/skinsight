# SkinSight — AI-Based Skin Condition Detection and Skin Care Recommendation System

SkinSight is an **academic image-screening prototype**, not a medical diagnostic system. It demonstrates a React/FastAPI workflow for image validation, quality heuristics, optional trained-model inference, Grad-CAM, educational information, and minimal local history. It does not diagnose, prescribe, choose personal treatment, replace professional assessment, or establish that an image contains a lesion.

The repository includes a smoke-test checkpoint for local demonstrations. `.env.example` selects this checkpoint by default; its held-out test accuracy is 49%, its predictions are unreliable, and it must not guide healthcare decisions. The app marks this model as demo-only. Replace it with a properly trained and evaluated model for research experiments, or set `MODEL_PATH` to an unavailable path to disable predictions. No dataset is bundled.

## Contents

- `frontend/`: React 18, TypeScript, Vite, Tailwind CSS, responsive SkinSight interface and Vitest tests.
- `backend/`: FastAPI REST API, upload/image-quality services, SQLAlchemy and local SQLite history, pytest tests.
- `ml/`: PyTorch/torchvision preprocessing, EfficientNet-B0/ConvNeXt-Tiny model factory, CSV dataset and splits, training, evaluation, inference and Grad-CAM.
- `data/`: dataset instructions and a clearly labelled synthetic CSV template.
- `models/`: model artifact instructions; no checkpoint is committed.
- `docs/`: architecture, dataset and API notes.

## Prerequisites

On Windows, install Python 3.11 or 3.12 (64-bit), Node.js 20+ (LTS recommended), Git, and VS Code. Use PowerShell. Python 3.12, Node 22 and pnpm 11 were used for development. PyTorch installation may use substantial disk space; CPU inference/training is supported. A compatible NVIDIA/CUDA setup is optional, not required. Pretrained torchvision weights are only fetched if `--pretrained` is explicitly supplied; the project does not automatically download datasets.

## Install in PowerShell

Open the project folder in VS Code, open a PowerShell terminal at the repository root, and run:

```powershell
# 1. Create and activate the Python virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# If PowerShell blocks activation for this session only:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# 2. Upgrade pip and install backend dependencies
python -m pip install --upgrade pip
python -m pip install -r .\backend\requirements.txt

# 3. Install pinned frontend workspace dependencies (pnpm 11)
corepack enable
corepack prepare pnpm@11.25.0 --activate
pnpm install --frozen-lockfile

# 4. Create your local environment file
Copy-Item .env.example .env
```

If Corepack is not available, install the pinned package manager with `npm install --global pnpm@11.25.0`, then run `pnpm install --frozen-lockfile`. Do not commit `.env`, local datasets, SQLite history, or model artifacts.

## Configure environment

Edit `.env` only if needed. Defaults are local-only: FastAPI uses `127.0.0.1:8000`, Vite uses `localhost:3000`, SQLite is stored at `backend/data/history.db`, maximum image size is 8 MB, and image retention is disabled. `CORS_ORIGINS` lists allowed development browser origins. `MODEL_PATH` points to the selected checkpoint file; its class mapping is read from the sibling `.classes.json` file. The example environment selects the unreliable 49%-accuracy smoke-test checkpoint and is for demonstration only. `CONFIDENCE_THRESHOLD` defaults to `0.55`; it affects uncertainty labeling but does not calibrate confidence. To make retention possible, an operator must explicitly set `ALLOW_IMAGE_RETENTION=true`; each uploader must then separately check the per-image retention box. Unchecking it leaves the image in memory only. The box does not appear when the operator has disabled retention. Retained local images are removed when their history record is deleted or history is cleared.

Never expose this development API publicly without adding appropriate authentication, rate limits, deployment storage policy, monitoring, and a security review. Uploaded health images can be sensitive. By default the application decodes images in memory, stores no image file, does not retain optional metadata, and saves only a minimal analysis history in a local SQLite database. Image retention requires both the operator setting and a separate per-upload user opt-in; history deletion removes the retained image. The browser temporarily uses an object URL for preview; it is revoked when the user clears the selection or changes it.

## Dataset placement

Obtain HAM10000 or a specific ISIC dataset through its official source and follow its current licence/terms. **No dataset is automatically downloaded.** Keep dataset files outside the source tree where practical. Create a CSV containing `image,label` and, where available, `patient_id`. Relative paths resolve against `--data-root` or the CSV's directory. See [`data/README.md`](data/README.md) for exact requirements, label mapping, patient-group splitting, and examples. Never treat the synthetic template as training data or claim dataset performance without a real held-out evaluation.

## Train an experiment

From the project root, with the virtual environment active:

```powershell
python -m ml.train --csv "D:\datasets\ham10000\manifest.csv" --data-root "D:\datasets\ham10000" --architecture efficientnet_b0 --epochs 10 --batch-size 16 --learning-rate 0.0003 --seed 42 --workers 0 --output "models\efficientnet_b0.pth"
```

Training defaults are documented in `ml/configs/default.json` and can be overridden with CLI flags. The default initializes EfficientNet-B0 randomly. To initialize from torchvision's ImageNet weights, add `--pretrained`; that may download weights from torchvision the first time. These generic weights alone are not a skin-condition model. Training writes the best-validation checkpoint, a `.classes.json` class mapping, and a `.metrics.json` report next to the chosen output path. The code attempts stratification and uses patient-group splits when patient IDs are provided, so the source identifiers must be correct. Review split sizes and class representation; tiny/imbalanced datasets may not support meaningful stratification. No data leakage method can correct incorrect source metadata.

For ConvNeXt-Tiny, set `--architecture convnext_tiny`. Evaluate an explicit independent labelled CSV using:

```powershell
python -m ml.evaluate --csv "D:\datasets\ham10000\held_out_test.csv" --data-root "D:\datasets\ham10000" --weights "models\efficientnet_b0.pth"
```

For one local image, the CLI uses the configured `MODEL_PATH` and the same quality/preprocessing contract:

```powershell
python -m ml.predict "D:\images\example.jpg"
```

Do not interpret academic metrics as clinical performance. HAM10000/ISIC dermoscopic imagery does not guarantee reliable predictions on everyday phone photos.

## Run the application

Use two PowerShell terminals from the repository root. Activate `.venv` in both if needed.

**Terminal 1 — FastAPI:**

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — React/Vite:**

```powershell
corepack pnpm dev
```

Open `http://localhost:3000`. Vite forwards `/api` requests to FastAPI at `127.0.0.1:8000`. The project is set up for managed preview on port 3000; local Windows commands use the same Vite port. API documentation is at `http://127.0.0.1:8000/docs` and the OpenAPI JSON is at `http://127.0.0.1:8000/openapi.json`.

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | App health and trained-model availability/message. |
| `GET` | `/api/classes` | Class names only if a valid trained model bundle is loaded. |
| `POST` | `/api/analyze` | Multipart `file` plus optional transient `age`, `body_location`, `symptom_duration`, and `symptoms` fields. |
| `GET` | `/api/history` | Up to 100 newest minimal history records. |
| `DELETE` | `/api/history/{id}` | Delete one history entry; returns 404 if absent. |
| `DELETE` | `/api/history` | Clear the local history. |

`POST /api/analyze` produces a structured quality report, model availability, uncertainty state, prediction/probabilities only when available, optional Grad-CAM, and educational content. The education panel is not a treatment plan; it gives general skin-care basics and advises prompt dermatologist review for concerning model labels. Invalid images return useful 4xx responses; oversize images return 413. See [`docs/api_documentation.md`](docs/api_documentation.md).

## Run tests and checks

```powershell
# Backend tests, from project root with .venv active
python -m pytest backend/tests -q

# Frontend unit tests
corepack pnpm test

# Frontend TypeScript production build
corepack pnpm build
```

## Common issues

- **PowerShell activation is blocked:** use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again; this changes policy only for the current shell.
- **`py -3.12` is unavailable:** install Python 3.12 x64, or create the environment with another supported Python 3.11/3.12 installation.
- **`pnpm` is not found:** enable Corepack with `corepack enable`, prepare the pinned release, or install pnpm globally as above.
- **Port 3000 or 8000 is busy:** stop the other process before launch; Vite's port is intentionally strict. If changing local ports, update `frontend/vite.config.ts` and the API CORS allowlist consistently. Managed preview expects port 3000.
- **Browser shows API/network error:** verify FastAPI is running on 8000 and use Vite's `http://localhost:3000` URL so `/api` is proxied.
- **Model unavailable:** train a model or set `MODEL_PATH` to a compatible checkpoint; keep the sibling `.classes.json` file present. A checkpoint must match the architecture, class mapping and torchvision/PyTorch implementation.
- **CUDA unavailable:** CPU fallback is expected and valid. Training may be slow; reduce batch size or epochs for experiments.
- **Image rejected:** use valid JPG/JPEG/PNG/WEBP content, correct extension/content, within the configured byte/dimension limits.
- **SQLite lock or test residue:** stop the API before removing `backend/data/history.db`. Tests use the local prototype database; do not run against a production/shared database.
- **Pretrained-weight download unavailable:** omit `--pretrained` to run from random initialization, or configure the weights in an approved offline cache. Randomly initialized weights are not a trained model and must not be loaded for user predictions.

## Safety and known limitations

The image quality check is a basic heuristic (blur, brightness, and resolution); it cannot establish that an image is a lesion, assess clinical suitability, or rule out disease. Softmax confidence is not necessarily a calibrated probability of correctness. Grad-CAM visualizes model attention rather than clinical reasoning or lesion localization. Education is generic and not personal medical advice or a treatment plan. Do not delay care based on model output. Seek qualified professional assessment for lesions that change, bleed, hurt, persist, or concern you. Dermoscopic research datasets do not guarantee generalization to smartphone photos, skin tones, devices, lighting, or clinical populations. The bundled demo checkpoint scored 49% on its held-out test split and is not suitable for healthcare decisions.
