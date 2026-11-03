# pyright: reportMissingImports=false

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import Settings
from models import AnalysisRecord
from session import initialize_database, make_engine, make_session_factory
from model_service import ModelService
from analysis import (
    AnalysisResponse,
    ClassesResponse,
    ClassProbability,
    EducationalRecommendation,
    HealthResponse,
    HistoryItem,
    ImageQualityReport,
    Prediction,
)
from image_input import ImageInputError, decode_uploaded_image
from image_quality import assess_image_quality
from recommendations import DISCLAIMER, recommendation_for

logger = logging.getLogger("skinsight")
settings = Settings.from_env()
engine = make_engine(settings.database_url)
SessionLocal = make_session_factory(engine)
model_service = ModelService(settings.model_path, model_version=settings.model_version)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database(engine)
    yield


app = FastAPI(
    title="SkinSight Academic Screening Prototype API",
    description=(
        "Educational image-screening prototype. It is not a medical diagnostic system. "
        "Model output is experimental and must not replace a qualified clinician."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Accept"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _stored_timestamp(record: AnalysisRecord):
    value = record.created_at
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _delete_retained_image(path_value: str | None) -> None:
    if not path_value:
        return
    try:
        candidate = Path(path_value).resolve()
        root = settings.retained_image_dir.resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            candidate.unlink()
    except OSError:
        logger.warning("A retained image could not be removed during history deletion.")


def _create_gradcam(tensor, image: Image.Image, class_index: int) -> tuple[str | None, str | None]:
    if model_service.model is None:
        return None, None
    try:
        from ml.gradcam import gradcam_overlay_data_url
        return gradcam_overlay_data_url(model_service.model, tensor.to(model_service.device), image, class_index), None
    except Exception:
        logger.warning("Grad-CAM generation failed for one analysis.")
        return None, "The model-attention visualization could not be generated for this image."


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_available=model_service.available,
        image_retention_allowed=settings.allow_image_retention,
        model_version=model_service.model_version if model_service.available else None,
        model_message=model_service.message,
    )


@app.get("/api/classes", response_model=ClassesResponse)
def classes() -> ClassesResponse:
    return ClassesResponse(
        classes=model_service.class_names if model_service.available else [],
        model_available=model_service.available,
    )


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    age: int | None = Form(default=None, ge=1, le=120),
    body_location: str | None = Form(default=None, max_length=80),
    symptom_duration: str | None = Form(default=None, max_length=80),
    symptoms: str | None = Form(default=None, max_length=160),
    retain_image: bool = Form(default=False),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    # Optional context is accepted for prototype usability but deliberately discarded, not logged or stored.
    _ = (age, body_location, symptom_duration, symptoms)
    try:
        # Bound read size irrespective of untrusted client headers.
        payload = await file.read(settings.max_upload_bytes + 1)
        image = decode_uploaded_image(
            file.filename,
            file.content_type,
            payload,
            max_bytes=settings.max_upload_bytes,
            max_dimension=settings.max_image_dimension,
        )
    except ImageInputError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    finally:
        await file.close()

    quality_data = assess_image_quality(
        image,
        min_dimension=settings.min_image_dimension,
        blur_threshold=settings.blur_threshold,
        dark_threshold=settings.dark_threshold,
        bright_threshold=settings.bright_threshold,
    )
    quality = ImageQualityReport.model_validate(quality_data)
    prediction: Prediction | None = None
    probabilities: list[ClassProbability] = []
    gradcam_data: str | None = None
    gradcam_message: str | None = None
    uncertainty = "image_unsuitable" if not quality.suitable else "model_unavailable"
    model_message = None if model_service.available else model_service.message
    model_version = model_service.model_version if model_service.available else None
    category: str | None = None
    confidence: float | None = None
    retained_path: str | None = None

    if quality.suitable and model_service.available:
        try:
            from ml.preprocess import preprocess_image
            tensor = preprocess_image(image)
            category, confidence, ranked, class_index = model_service.predict(tensor)
            prediction = Prediction(visual_category=category, confidence=confidence)
            probabilities = [ClassProbability.model_validate(item) for item in ranked]
            if confidence < settings.confidence_threshold or model_service.model_version == "smoke-1000-images":
                uncertainty = "low_confidence"
            else:
                uncertainty = "confident"
            gradcam_data, gradcam_message = _create_gradcam(tensor, image, class_index)
        except Exception:
            logger.warning("Analysis inference failed; no prediction was stored.")
            prediction = None
            probabilities = []
            category = None
            confidence = None
            uncertainty = "model_unavailable"
            model_message = "The trained model could not analyze this image. No prediction is available."

    if retain_image and settings.allow_image_retention:
        try:
            settings.retained_image_dir.mkdir(parents=True, exist_ok=True)
            destination = settings.retained_image_dir / f"{uuid4().hex}.jpg"
            image.save(destination, format="JPEG", quality=92)
            retained_path = str(destination.resolve())
        except OSError:
            logger.warning("Explicit image retention failed; the analysis continues without saving the image.")

    record = AnalysisRecord(
        predicted_category=category,
        confidence=confidence,
        quality_status=quality.status,
        model_version=model_version,
        image_path=retained_path,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    if uncertainty == "image_unsuitable":
        model_message = "This image did not meet the configured minimum dimension heuristic. Please provide a clearer, higher-resolution image."

    return AnalysisResponse(
        analysis_id=record.id,
        created_at=_stored_timestamp(record),
        image_retained=bool(retained_path),
        quality=quality,
        model_status="available" if model_service.available else "unavailable",
        model_message=model_message,
        uncertainty_status=uncertainty,
        prediction=prediction,
        probabilities=probabilities,
        gradcam_data_url=gradcam_data,
        gradcam_available=bool(gradcam_data),
        gradcam_message=gradcam_message,
        recommendation=EducationalRecommendation.model_validate(recommendation_for(category)),
        disclaimer=DISCLAIMER,
    )


@app.get("/api/history", response_model=list[HistoryItem])
def get_history(db: Session = Depends(get_db)) -> list[HistoryItem]:
    records = db.scalars(select(AnalysisRecord).order_by(AnalysisRecord.created_at.desc()).limit(100)).all()
    return [HistoryItem.model_validate(record) for record in records]


@app.delete("/api/history/{record_id}")
def delete_history_item(record_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    record = db.get(AnalysisRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="History record was not found.")
    retained_path = record.image_path
    db.delete(record)
    db.commit()
    _delete_retained_image(retained_path)
    return {"deleted": True, "id": record_id}


@app.delete("/api/history")
def clear_history(db: Session = Depends(get_db)) -> dict[str, object]:
    retained_paths = db.query(AnalysisRecord.image_path).filter(AnalysisRecord.image_path.is_not(None)).all()
    deleted = db.query(AnalysisRecord).delete(synchronize_session=False)
    db.commit()
    for (path_value,) in retained_paths:
        _delete_retained_image(path_value)
    return {"deleted": True, "count": deleted}
