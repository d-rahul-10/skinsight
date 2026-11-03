# Architecture and data flow

## Components

```text
Browser (React + TypeScript + Vite :3000)
  ├── local file validation and in-memory preview
  └── same-origin /api requests (Vite proxy in local development)
          ↓ multipart upload
FastAPI :8000
  ├── strict byte/format/content/dimension validation
  ├── in-memory Pillow decode → OpenCV quality heuristics
  ├── shared ImageNet preprocessing → ModelService (only with compatible trained bundle)
  ├── optional Grad-CAM → data URL in analysis response
  ├── static reviewed educational copy
  └── SQLite + SQLAlchemy minimal history (never image bytes or metadata)

Training pipeline (ml/)
  ├── CSV/path/label validation
  ├── patient-grouped split when patient_id exists; stratified split otherwise if suitable
  ├── train-only augmentation and identical inference normalization
  ├── EfficientNet-B0 default; ConvNeXt-Tiny extension
  └── best-validation weights + class mapping + held-out metrics report
```

## Frontend

`frontend/src/App.tsx` implements the single-page landing, upload and results experience. `services/api.ts` owns REST operations and upload progress; `utils/uploadValidation.ts` applies a client-side convenience check, while backend content validation remains authoritative. Browser image previews use `URL.createObjectURL` and are revoked when cleared. The `public/manus-routes.json` manifest declares the one implemented page route (`/`). Tailwind is configured alongside custom semantic CSS for the distinctive visual system.

## Backend

`backend/app/main.py` is the FastAPI entry point and owns `/api/health`, `/api/classes`, `/api/analyze` and history routes. `services/image_input.py` enforces extension/content agreement, format allowlist, bounded size/dimensions, and successful decode. `services/image_quality.py` is an explicit heuristic, not a lesion detector. `ml/model_service.py` loads only a strict, compatible state dictionary and matching `.classes.json`; no implicit default/pretrained inference occurs. Optional metadata is bounded by FastAPI form validation and intentionally ignored after the request. It is neither logged nor persisted.

SQLite stores timestamp, quality status, model version, and category/confidence only when the trained model produces them. Images are not stored by default. Retention requires both `ALLOW_IMAGE_RETENTION=true` at the local operator level and a separate checkbox for the individual upload; a UUID filename is used and deleting its history row or clearing history removes the image. Model classes and their educational explanations are explicitly separated: a category string never becomes an individual diagnosis.

## Machine learning

`ml/preprocess.py` shares 224×224 RGB/ImageNet normalization. Augmentation is applied only to the training loader. `ml/dataset.py` rejects missing inputs and blank labels and splits by patient group when identifiers are available. Model artifacts include a `.classes.json` sidecar describing class order, architecture, and model version. Evaluation reports accuracy, macro precision/recall/F1, and a confusion matrix. Training metrics do not imply clinical performance or smartphone-photo generalization.

Grad-CAM hooks are registered for a single call and removed in `finally`; its image is optional and failures do not invalidate a prediction. The overlay explains model attention only and cannot be read as clinical reasoning or lesion localization.

## Data and trust boundaries

The browser preview and response image remain in browser memory. The API reads only a bounded amount of multipart content, decodes without writing to disk, and returns user-safe errors. SQLite content deliberately excludes original filenames, image data, and optional metadata. Logs exclude image contents and user metadata. CORS is restricted to configured local origins. Deployment requires separate security/privacy review; a local academic prototype is not a secure clinical service.
