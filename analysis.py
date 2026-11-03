from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ImageQualityReport(BaseModel):
    status: Literal["good", "warning", "unsuitable"]
    suitable: bool
    warnings: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    metrics: dict[str, float | int] = Field(default_factory=dict)


class Prediction(BaseModel):
    visual_category: str
    confidence: float = Field(ge=0.0, le=1.0)


class ClassProbability(BaseModel):
    category: str
    probability: float = Field(ge=0.0, le=1.0)


class EducationalRecommendation(BaseModel):
    title: str
    information: str
    general_guidance: list[str] = Field(default_factory=list)
    care_notice: str
    limitation: str


class AnalysisResponse(BaseModel):
    analysis_id: int
    created_at: datetime
    image_retained: bool = False
    quality: ImageQualityReport
    model_status: Literal["available", "unavailable"]
    model_message: str | None = None
    uncertainty_status: Literal["confident", "low_confidence", "model_unavailable", "image_unsuitable"]
    prediction: Prediction | None = None
    probabilities: list[ClassProbability] = Field(default_factory=list)
    gradcam_data_url: str | None = None
    gradcam_available: bool = False
    gradcam_message: str | None = None
    recommendation: EducationalRecommendation
    disclaimer: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_available: bool
    image_retention_allowed: bool = False
    model_version: str | None = None
    model_message: str


class ClassesResponse(BaseModel):
    classes: list[str]
    model_available: bool


class HistoryItem(BaseModel):
    id: int
    created_at: datetime
    predicted_category: str | None
    confidence: float | None
    quality_status: str
    model_version: str | None
    image_retained: bool = False

    model_config = {"from_attributes": True}
