# Project outcomes and acceptance criteria

This tracker records the requested product behavior. Items stay open until implemented and supported by evidence.

## 1. Responsive public-facing experience and upload flow — [x]
- Create a polished responsive home page with application name and navigation, a hero explaining the system, a primary “Analyze Skin Image” button, how-it-works section, features and limitations, privacy information, medical disclaimer, and project footer.
- Use white backgrounds, soft violet and blue accents, subtle gradients, rounded cards, clean typography, responsive desktop/mobile layouts, consistent spacing and accessible forms/buttons.
- Provide reusable components, loading/skeleton states, inline feedback or toast notifications, empty/error states, and a polished results page. Do not use nonfunctional buttons, placeholder links, fake charts, or static results presented as real inference.
- Provide a drag-and-drop and computer file-picker upload, image preview, supported JPG/JPEG/PNG/WEBP formats, file type and size validation, upload progress/loading indicators, clear errors, remove/replace control, and optional age/body location/symptom duration/symptoms fields. Do not require unnecessary personal information.
- After results, allow analyzing another image.

## 2. Secure upload, quality report, preprocessing, and privacy — [x]
- Validate file extension and actual content, supported format, file size, and corrupted/invalid images; use safe temporary-file handling, path traversal protections, no uploaded-file execution, restricted CORS, input validation, environment-based configuration, and safe logs that exclude image contents and unnecessary personal information. Do not expose filesystem paths, stack traces, secrets, or sensitive information in API responses.
- Before classification assess sharpness/blur with a documented Laplacian-variance heuristic; excessive darkness/brightness; dimensions/resolution; and suitability for processing using documented heuristics. Return a structured quality report with status, warnings, and reasons. Gracefully report unsuitable inputs.
- Do not claim quality heuristics can reliably determine whether an image contains a lesion. If suitability cannot be established, warn and request a clearer image.
- Implement reusable preprocessing to convert to RGB, resize to model-required dimensions, normalize with the selected pretrained model's expected normalization, and create tensor transforms. Use augmentation only during training. Gracefully handle preprocessing errors and use the same configuration for train/validation/test/inference where appropriate.
- Explain that uploads may contain sensitive health information, how images are processed/stored, and the retention behavior. Do not retain uploaded images permanently by default; retention must be optional and explicit.

## 3. Dataset preparation and training/evaluation pipeline — [x]
- Provide a modular EfficientNet-B0 transfer-learning pipeline using a supported torchvision pretrained-weights API, with classifier replacement matching configured dataset classes and architecture extensible to ConvNeXt.
- Support training, validation, testing, inference, reproducible random seeds, GPU when available and CPU fallback, configurable batch size/epochs/learning rate/model paths, saved weights and class mappings, training-loss/validation-metric tracking, justified class-imbalance handling, prevention of data leakage, and best-model selection based on validation performance.
- Read image paths and labels from CSV; validate missing files and invalid labels; create stratified train/validation/test splits when suitable; use patient-level grouping when patient identifiers exist; document dataset preparation and class mapping; keep datasets outside source where practical; and do not automatically download large datasets.
- Support publicly available HAM10000 and ISIC datasets with dataset-specific labels used correctly. Include a small synthetic metadata example or clearly labelled demonstration mode when real data is absent. Do not imply dermoscopic training images guarantee reliable predictions on ordinary smartphone photographs.
- Report classification accuracy, precision, recall, F1-score, and a confusion matrix. Do not invent accuracy, pretend a model was trained without data/weights, or fabricate datasets or model predictions.

## 4. Honest inference, confidence, and unknown cases — [x]
- Load a compatible trained model and return the predicted visual category, model confidence, ranked class probabilities where appropriate, image-quality assessment, and clear uncertainty status.
- Implement a configurable confidence threshold. On low confidence display exactly: “The model is uncertain about this image. Please upload a clearer image or consult a qualified dermatologist.”
- Explain that softmax confidence is not necessarily a calibrated probability of diagnostic correctness.
- If weights are missing, untrained, incompatible, fail to load, or inference otherwise cannot run, show an honest unavailable-model message. Never produce a fake prediction or fabricated confidence score. Keep unit-test mock models separate from production inference.

## 5. Grad-CAM explainability — [x]
- Implement Grad-CAM for the selected EfficientNet convolutional layer; register and remove hooks safely; generate a heatmap for the predicted class; resize to original image dimensions; overlay it on the uploaded image; and handle failures without crashing.
- Show original image and Grad-CAM side by side and provide a visualization download option.
- Label the visualization as an explanation of model attention, not proof of medical reasoning or lesion localization.

## 6. Grounded educational recommendations and result dashboard — [x]
- Provide a configurable reviewed educational recommendation module for every supported category with general educational information, basic non-prescriptive skin-care guidance where appropriate, image-classification limitations, and advice to seek professional assessment when a lesion is changing, bleeding, painful, persistent, or concerning, including uncertainty messaging.
- Never prescribe medicines, diagnose cancer, recommend delaying care because of a model prediction, or generate unsupported personalized treatments using an LLM. Clearly distinguish general skin-care guidance from medical advice.
- Results display the uploaded image, quality status/warnings, predicted visual category and confidence only if a valid trained-model prediction exists, class probability chart only for valid real inference, Grad-CAM result when available, educational information/recommendations, low-confidence and unavailable-model warnings, medical disclaimer, and an analyze-another option. Never show hardcoded demo predictions as real results.

## 7. SQLite history and deletion — [x]
- Use SQLite and SQLAlchemy for analysis history containing timestamp, predicted category and confidence when available, quality-assessment status, and model version. Do not store unnecessary sensitive metadata or permanently retain images by default; image retention is optional and explicit.
- Provide GET /api/history, DELETE /api/history/{id}, and DELETE /api/history; provide a usable history-deletion experience and explain application retention behavior.

## 8. FastAPI REST contract and runtime behavior — [x]
- Implement GET /api/health for application/model availability; GET /api/classes for configured model class names; POST /api/analyze for image upload and analysis; GET /api/history; DELETE /api/history/{id}; and DELETE /api/history.
- Use JSON responses, multipart uploads, appropriate HTTP status codes, Pydantic request/response schemas, upload validation, clear error handling, and FastAPI Swagger documentation. Keep frontend/backend API contracts consistent.
- Return no internal filesystem paths, stack traces, secrets, or sensitive information. Keep the application runnable on standard Windows.

## 9. Project structure, configuration, and documentation — [x]
- Keep frontend, backend, ML, data, model artifacts and documentation separate. Provide frontend/src components/pages/services/hooks/types/utils and App.tsx; backend/app API/core/models/schemas/services/ML/database modules, tests, and main.py; ML train/evaluate/predict/gradcam/preprocess/dataset/configs; data/README.md; models/README.md; docs architecture/dataset/API documents; .env.example; .gitignore; and README with exact Windows run instructions.
- Use environment variables via .env and .env.example; no hardcoded credentials/API keys. Use stable compatible versions, type hints, modular functions, minimal duplication, graceful exceptions and no modification of unrelated files.
- README covers prerequisites, project installation, Python virtualenv creation, dependency installation, frontend dependency installation, environment-variable configuration, dataset placement, model training, FastAPI start, React/Vite start, tests, and common errors. Provide exact Windows PowerShell-compatible commands; do not assume an existing virtualenv or pretrained model.
- Document dataset CSV format, HAM10000/ISIC preparation, dataset placement/download instructions without automatic downloads, class mapping, training and evaluation instructions, architecture, API endpoints, limitations, privacy and non-diagnostic purpose.

## 10. Automated tests and evidence-based verification — [x]
- Add pytest tests for API health, supported/unsupported formats, empty/oversized/corrupted uploads, quality assessment, preprocessing, missing/unloadable model weights, prediction response validation, low-confidence handling, Grad-CAM generation, SQLite history and deletion.
- Add Vitest tests for frontend upload validation and API error handling. Use mock models only for unit tests and keep them separated from production inference.
- Run available backend and frontend tests, fix implementation errors, and report tests that cannot run. Verify frontend/backend integration without claiming tests passed unless they were executed successfully.
- Final delivery contains actual source code, directory tree, installation/execution instructions, dataset format/preparation instructions, model training/evaluation instructions, API documentation, test results, known limitations, a feature verification checklist, and exact Windows VS Code commands. If datasets/weights are absent, complete all possible components and explain precisely how to add them; provide the full training pipeline and honest unavailable-model state.

## Verification notes

- Backend: `python3 -m pytest backend/tests -q` — 21 passed; one upstream Starlette deprecation warning. Python compileall and `ml.train --help` / `ml.evaluate --help` also passed.
- Frontend: `pnpm --filter frontend test` — 4 passed; `pnpm --filter frontend build` passed TypeScript and Vite production bundling.
- Runtime integration: Vite served the page and exact `/manus-routes.json`; its `/api` proxy reached FastAPI health/classes/analyze. A valid image produced a quality report with no fabricated prediction because no task-trained model bundle is provided.
- External/data dependency: no HAM10000/ISIC files or trained weights were supplied. Training/evaluation on real data and real-model inference/Grad-CAM remain to be performed by the operator after preparing a licensed dataset. No model metrics or accuracy are claimed.
