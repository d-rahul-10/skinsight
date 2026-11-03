# API documentation

The FastAPI interactive Swagger UI is served at `/docs`; OpenAPI JSON is at `/openapi.json` while the backend is running. In local development use `http://127.0.0.1:8000`; from the frontend, same-origin `/api` requests are proxied by Vite. All JSON errors use FastAPI's `detail` message shape.

## `GET /api/health`

Returns 200 when the application is running:

```json
{"status":"ok","model_available":false,"image_retention_allowed":false,"model_version":null,"model_message":"No trained model weights are installed. Add a trained checkpoint to enable inference."}
```

When a valid trained bundle exists, `model_available` is true and `model_version` is populated. No fabricated health accuracy is provided.

## `GET /api/classes`

Returns the exact configured trained class mapping if a model bundle loads; otherwise returns `{"classes":[],"model_available":false}`.

## `POST /api/analyze`

Content type: `multipart/form-data`. Required field: `file` (JPG/JPEG/JPE/PNG/WEBP). Optional transient fields: `age` (1–120), `body_location` (max 80 chars), `symptom_duration` (max 80), `symptoms` (max 160). The API ignores these optional values after validation: they are not used for prediction, stored, or logged. Optional `retain_image=true` is honored only when the local operator has set `ALLOW_IMAGE_RETENTION=true`; by default this setting is false. Both the operator's enablement and the user's per-upload consent are required.

The response includes `analysis_id`, UTC `created_at`, `image_retained`, a structured `quality` report (`status`, `suitable`, `warnings`, `reasons`, `metrics`), `model_status`, uncertainty state, optional prediction/probabilities/Grad-CAM, static educational recommendation, and disclaimer. When weights are unavailable or image resolution is unsuitable, prediction and probability arrays are empty/null; no confidence is invented. `uncertainty_status` is one of `confident`, `low_confidence`, `model_unavailable`, or `image_unsuitable`.

Status handling: 200 for an accepted/assessed image (including an honest model-unavailable result); 400 for unsupported, corrupt, extension/content-mismatched images or empty file data; 413 for byte/dimension limits; 422 for missing file or invalid optional form values. Responses do not expose filesystem paths or stack traces. Upload limit defaults to 8 MB, configured using `MAX_UPLOAD_MB`. Dimensions have a default maximum of 8192 pixels per side.

## `GET /api/history`

Returns up to 100 newest entries with `id`, UTC timestamp, optional prediction/confidence, quality status, and optional model version. Original images and optional form fields are never stored.

## `DELETE /api/history/{id}`

Deletes one record, returning `{"deleted":true,"id":...}`; returns 404 if no record exists.

## `DELETE /api/history`

Clears all local analysis history and returns `{"deleted":true,"count":...}`.

## Browser safety notes

The quality report uses non-diagnostic heuristics: Laplacian variance for blur, mean brightness, and minimum dimensions. Warnings are not proof that an image contains or does not contain a lesion. Softmax confidence is uncalibrated unless separately validated; this project does not claim calibration. Grad-CAM is an attention visualization, not lesion localization. All displayed skin-care copy is general educational information and not medical advice.
