# SkinSight

SkinSight is an educational skin-image screening prototype. It can show an image-model category and general skin-care information, but it cannot diagnose or choose a personal treatment. This repository does not include model weights or medical datasets; without a compatible model bundle, the API reports that no prediction is available.

The app also includes general daily skin-care and food guidance, plus an optional skin diary and follow-up reminders. Diary entries and reminders stay in the current browser's local storage and do not include uploaded photos. Optional browser alerts only work while the app is open. Avoid entering identifying health information; this is not a medical record or a replacement for clinician advice.

## Run locally

Install the Python and Node dependencies, then start the API and frontend in separate terminals:

```powershell
python -m pip install -r requirements.txt
npm install
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
npm run dev
```

The UI is served at `http://localhost:3000` and the API docs at `http://127.0.0.1:8000/docs`.

## Model weights and limitations

The repository intentionally excludes model weights and datasets. To run inference, supply a compatible trained checkpoint and its adjacent `.classes.json` mapping, then set `MODEL_PATH` in `.env`. Without those files, the API returns no prediction. Model outputs are experimental and are not medical advice or a substitute for clinical assessment. Any smoke-test checkpoint used during development is unreliable and must not guide healthcare decisions.

After copying `.env.example` to `.env`, the app is ready to run without model weights; upload analysis will clearly indicate when no prediction can be produced. Restart the API after changing `.env`. Use only a properly trained and independently evaluated model bundle for research experiments; do not treat dataset metrics as clinical validation.

For a dataset arranged in one image folder per class, create a manifest and train with DenseNet-121, as in the referenced Kaggle notebook:

```powershell
python build_manifest.py --data-root "C:\path\to\IMG_CLASSES" --output "runs\img_classes_manifest.csv"
python train.py --csv "runs\img_classes_manifest.csv" --architecture densenet121 --output "models\densenet121.pth" --workers 0
```

For an existing manifest, use `python train.py --csv "C:\path\to\manifest.csv" --data-root "C:\path\to\images"`. The manifest must include `image,label` columns and may include a `patient_id` column; see [Dataset preparation guide](./Dataset%20preparation%20guide.md). Training saves a `.classes.json` mapping and `.metrics.json` held-out test report alongside the checkpoint. Short smoke runs verify the pipeline only; their checkpoints are not suitable for healthcare use. To use a trained bundle, set `MODEL_PATH` in `.env` to the checkpoint path. Keep private datasets and model weights out of version control, and review dataset/model licenses before use. `--pretrained` uses ImageNet initialization only; pass `--no-pretrained` to train from random initialization. ImageNet weights are not a skin-condition-trained model.

## Checks

```powershell
pytest -q
npm test
npm run build
```
