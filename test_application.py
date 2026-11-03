from __future__ import annotations

import io
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

import main as api
from image_input import ImageInputError, decode_uploaded_image
from image_quality import assess_image_quality
from ml.gradcam import gradcam_overlay_data_url
from ml.preprocess import preprocess_image
from recommendations import recommendation_for


def make_png(size: tuple[int, int] = (256, 256), *, color: tuple[int, int, int] = (152, 105, 94)) -> bytes:
    buffer = io.BytesIO()
    if size == (256, 256):
        rng = np.random.default_rng(7)
        pixels = rng.integers(95, 176, size=(size[1], size[0], 3), dtype=np.uint8)
        Image.fromarray(pixels, mode="RGB").save(buffer, format="PNG")
    else:
        Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_image_decoder_accepts_supported_png_as_rgb() -> None:
    image = decode_uploaded_image("lesion.png", "image/png", make_png(), max_bytes=1024 * 1024, max_dimension=2048)
    assert image.mode == "RGB"
    assert image.size == (256, 256)


def test_image_decoder_accepts_jpe_extension_for_jpeg_content() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (256, 256), "tan").save(buffer, format="JPEG")
    image = decode_uploaded_image(
        "pasted-image.jpe", "image/jpeg", buffer.getvalue(), max_bytes=1024 * 1024, max_dimension=2048
    )
    assert image.size == (256, 256)
    assert image.mode == "RGB"


@pytest.mark.parametrize("filename,content_type,payload", [
    ("photo.gif", "image/gif", b"GIF89a"),
    ("photo.png", "image/png", b"not an image"),
    ("photo.jpg", "image/jpeg", make_png()),
    ("photo.png", "image/jpeg", make_png()),
], ids=["unsupported-extension", "corrupt-content", "jpeg-name-with-png-content", "png-name-with-jpeg-content"])
def test_image_decoder_rejects_unsupported_mismatched_or_corrupt_content(filename, content_type, payload) -> None:
    with pytest.raises(ImageInputError):
        decode_uploaded_image(filename, content_type, payload, max_bytes=1024 * 1024, max_dimension=2048)


def test_image_decoder_rejects_empty_and_oversized_payloads() -> None:
    with pytest.raises(ImageInputError, match="empty"):
        decode_uploaded_image("x.png", "image/png", b"", max_bytes=32, max_dimension=2048)
    with pytest.raises(ImageInputError) as error:
        decode_uploaded_image("x.png", "image/png", b"x" * 33, max_bytes=32, max_dimension=2048)
    assert error.value.status_code == 413


def test_quality_assessment_reports_blur_and_resolution_metrics() -> None:
    image = Image.new("RGB", (64, 96), (15, 15, 15))
    report = assess_image_quality(image, min_dimension=128, blur_threshold=35, dark_threshold=35)
    assert report["status"] == "unsuitable"
    assert report["suitable"] is False
    assert report["metrics"]["width"] == 64
    assert report["metrics"]["laplacian_variance"] == 0.0
    assert report["warnings"]
    assert report["reasons"]


def test_quality_assessment_warns_for_brightness_without_claiming_lesion_detection() -> None:
    report = assess_image_quality(Image.new("RGB", (256, 256), "white"), blur_threshold=0)
    assert report["status"] == "warning"
    assert report["suitable"] is True
    assert any("bright" in item for item in report["warnings"])


def test_preprocessing_returns_imagenet_normalized_rgb_tensor() -> None:
    tensor = preprocess_image(Image.new("L", (80, 100), 128))
    assert tuple(tensor.shape) == (1, 3, 224, 224)
    assert torch.isfinite(tensor).all()


def test_missing_weights_are_reported_without_fabricated_classes(tmp_path: Path) -> None:
    from model_service import ModelService
    service = ModelService(tmp_path / "missing.pth")
    assert service.available is False
    assert service.class_names == []
    assert "No trained model weights" in service.message
    with pytest.raises(RuntimeError):
        service.predict(torch.zeros((1, 3, 224, 224)))


def test_gradcam_overlay_is_generated_and_hook_is_removed() -> None:
    from torch import nn

    class TinyClassifier(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.features = nn.Sequential(nn.Conv2d(3, 4, kernel_size=3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1))
            self.head = nn.Linear(4, 2)
        def forward(self, value):
            return self.head(self.features(value).flatten(1))

    model = TinyClassifier().eval()
    handles_before = len(model.features[0]._forward_hooks)
    result = gradcam_overlay_data_url(model, torch.randn(1, 3, 32, 32), Image.new("RGB", (64, 48), "tan"), 0)
    assert result.startswith("data:image/png;base64,")
    assert len(model.features[0]._forward_hooks) == handles_before


def test_api_health_and_classes_honestly_report_missing_model(monkeypatch, tmp_path: Path) -> None:
    from model_service import ModelService

    monkeypatch.setattr(api, "model_service", ModelService(tmp_path / "missing.pth"))
    with TestClient(api.app) as client:
        health = client.get("/api/health")
        classes = client.get("/api/classes")
    assert health.status_code == 200
    assert health.json()["model_available"] is False
    assert classes.status_code == 200
    assert classes.json() == {"classes": [], "model_available": False}


def test_api_rejects_missing_upload_and_unsupported_format() -> None:
    with TestClient(api.app) as client:
        empty = client.post("/api/analyze")
        unsupported = client.post("/api/analyze", files={"file": ("image.gif", b"GIF89a", "image/gif")})
    assert empty.status_code == 422
    assert unsupported.status_code == 400
    assert "Unsupported image format" in unsupported.json()["detail"]
    assert "/home/" not in unsupported.text


def test_api_analyze_does_not_invent_prediction_and_history_deletes(monkeypatch, tmp_path: Path) -> None:
    from model_service import ModelService

    monkeypatch.setattr(api, "model_service", ModelService(tmp_path / "missing.pth"))
    with TestClient(api.app) as client:
        response = client.post("/api/analyze", files={"file": ("image.png", make_png(), "image/png")})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["model_status"] == "unavailable"
        assert body["prediction"] is None
        assert body["probabilities"] == []
        assert body["image_retained"] is False
        assert body["uncertainty_status"] == "model_unavailable"
        assert "No trained model weights" in body["model_message"]
        assert body["quality"]["status"] == "good"
        assert "gradcam_data_url" not in body or body["gradcam_data_url"] is None
        assert "not a medical diagnostic" in body["disclaimer"].lower()
        row_id = body["analysis_id"]
        history = client.get("/api/history")
        assert history.status_code == 200
        assert any(item["id"] == row_id and item["predicted_category"] is None for item in history.json())
        deleted = client.delete(f"/api/history/{row_id}")
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
        assert client.delete(f"/api/history/{row_id}").status_code == 404
        clear = client.delete("/api/history")
        assert clear.status_code == 200
        assert clear.json()["deleted"] is True


def test_api_unsuitable_image_requests_clearer_image_without_prediction() -> None:
    with TestClient(api.app) as client:
        response = client.post("/api/analyze", files={"file": ("small.png", make_png((64, 64)), "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["quality"]["status"] == "unsuitable"
    assert body["uncertainty_status"] == "image_unsuitable"
    assert body["prediction"] is None
    assert "clearer" in body["model_message"].lower()


def test_image_retention_requires_operator_flag_and_explicit_upload_choice(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "settings",
        replace(api.settings, allow_image_retention=True, retained_image_dir=tmp_path),
    )
    with TestClient(api.app) as client:
        response = client.post(
            "/api/analyze",
            files={"file": ("image.png", make_png(), "image/png")},
            data={"retain_image": "true"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["image_retained"] is True
        retained = list(tmp_path.glob("*.jpg"))
        assert len(retained) == 1
        history = client.get("/api/history").json()
        item = next(value for value in history if value["id"] == body["analysis_id"])
        assert item["image_retained"] is True
        assert "image_path" not in item
        deletion = client.delete(f"/api/history/{body['analysis_id']}")
        assert deletion.status_code == 200
        assert retained[0].exists() is False


def test_api_marks_mock_model_output_as_low_confidence_and_returns_ranked_probabilities(monkeypatch) -> None:
    monkeypatch.setattr(api.model_service, "model", torch.nn.Identity())
    monkeypatch.setattr(api.model_service, "class_names", ["mel", "nv"])
    monkeypatch.setattr(api.model_service, "model_version", "unit-test-mock")
    monkeypatch.setattr(
        api.model_service,
        "predict",
        lambda _tensor: (
            "nv",
            0.42,
            [{"category": "nv", "probability": 0.42}, {"category": "mel", "probability": 0.58}],
            1,
        ),
    )
    monkeypatch.setattr(api, "_create_gradcam", lambda *_args: (None, "Test Grad-CAM unavailable."))
    with TestClient(api.app) as client:
        response = client.post("/api/analyze", files={"file": ("mock.png", make_png(), "image/png")})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["model_status"] == "available"
    assert body["uncertainty_status"] == "low_confidence"
    assert body["prediction"] == {"visual_category": "nv", "confidence": 0.42}
    assert body["probabilities"][0]["category"] == "nv"
    assert body["recommendation"]["title"] == "Melanocytic nevus (mole) model label"
    assert body["gradcam_message"] == "Test Grad-CAM unavailable."


def test_api_recommends_dermatologist_for_concerning_predicted_label(monkeypatch) -> None:
    monkeypatch.setattr(api.model_service, "model", torch.nn.Identity())
    monkeypatch.setattr(api.model_service, "class_names", ["Melanoma", "nv"])
    monkeypatch.setattr(api.model_service, "model_version", "unit-test-mock")
    monkeypatch.setattr(
        api.model_service,
        "predict",
        lambda _tensor: (
            "Melanoma",
            0.8,
            [{"category": "Melanoma", "probability": 0.8}, {"category": "nv", "probability": 0.2}],
            0,
        ),
    )
    monkeypatch.setattr(api, "_create_gradcam", lambda *_args: (None, None))

    with TestClient(api.app) as client:
        response = client.post("/api/analyze", files={"file": ("mock.png", make_png(), "image/png")})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prediction"]["visual_category"] == "Melanoma"
    assert body["recommendation"]["title"] == "Melanoma model label"
    assert "qualified dermatologist" in body["recommendation"]["care_notice"]
    assert "not a diagnosis" in body["recommendation"]["care_notice"]


def test_demo_checkpoint_always_shows_uncertainty_even_with_high_softmax(monkeypatch) -> None:
    monkeypatch.setattr(api.model_service, "model", torch.nn.Identity())
    monkeypatch.setattr(api.model_service, "class_names", ["nv", "mel"])
    monkeypatch.setattr(api.model_service, "model_version", "smoke-1000-images")
    monkeypatch.setattr(
        api.model_service,
        "predict",
        lambda _tensor: (
            "nv",
            0.99,
            [{"category": "nv", "probability": 0.99}, {"category": "mel", "probability": 0.01}],
            0,
        ),
    )
    monkeypatch.setattr(api, "_create_gradcam", lambda *_args: (None, None))

    with TestClient(api.app) as client:
        response = client.post("/api/analyze", files={"file": ("mock.png", make_png(), "image/png")})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["uncertainty_status"] == "low_confidence"


@pytest.mark.parametrize(
    ("category", "expected_title"),
    [
        ("Atopic Dermatitis", "Atopic dermatitis model label"),
        ("Basal Cell Carcinoma (BCC)", "Basal cell carcinoma (BCC) model label"),
        ("Benign Keratosis-like Lesions (BKL)", "Benign keratosis-like (BKL) model label"),
        ("Eczema", "Eczema model label"),
        ("Melanocytic Nevi (NV)", "Melanocytic nevus (mole) model label"),
        ("Melanoma", "Melanoma model label"),
        (
            "Psoriasis pictures Lichen Planus and related diseases",
            "Psoriasis model label",
        ),
        (
            "Seborrheic Keratoses and other Benign Tumors",
            "Seborrheic keratosis model label",
        ),
        ("Tinea Ringworm Candidiasis and other Fungal Infections", "Fungal-infection model label"),
        ("Warts Molluscum and other Viral Infections", "Viral skin-condition model label"),
    ],
)
def test_recommendations_recognize_bundled_demo_classes(category: str, expected_title: str) -> None:
    recommendation = recommendation_for(category)
    assert recommendation["title"] == expected_title
    assert recommendation["limitation"].find("not a diagnosis") >= 0
    assert recommendation["limitation"].find("personal treatment") >= 0


@pytest.mark.parametrize(
    "category",
    ["AKIEC", "Basal Cell Carcinoma (BCC)", "Melanoma", "Squamous Cell Carcinoma"],
)
def test_concerning_model_labels_recommend_prompt_dermatologist_review(category: str) -> None:
    notice = recommendation_for(category)["care_notice"].lower()
    assert "qualified dermatologist" in notice
    assert "prompt review" in notice
    assert "not a diagnosis" in notice
    assert "do not start treatment" in notice


def test_unknown_category_does_not_claim_a_condition_or_recommend_treatment() -> None:
    recommendation = recommendation_for("unmapped class")
    assert recommendation["title"] == "General skin-care information"
    assert "cannot recommend personal treatment" in recommendation["limitation"]


def test_api_enforces_server_upload_byte_limit(monkeypatch) -> None:
    monkeypatch.setattr(api, "settings", replace(api.settings, max_upload_bytes=100))
    with TestClient(api.app) as client:
        response = client.post("/api/analyze", files={"file": ("large.png", make_png(), "image/png")})
    assert response.status_code == 413
    assert "upload limit" in response.json()["detail"].lower()


def test_patient_group_split_has_no_patient_overlap() -> None:
    import pandas as pd
    from ml.dataset import split_manifest

    rows = []
    for patient_index in range(40):
        label = "class_a" if patient_index % 2 == 0 else "class_b"
        for view in range(2):
            rows.append({"image": f"p{patient_index}_{view}.jpg", "label": label, "patient_id": f"p{patient_index}"})
    split = split_manifest(pd.DataFrame(rows), seed=23)
    patients = {name: set(frame["patient_id"]) for name, frame in split.items()}
    assert patients["train"].isdisjoint(patients["validation"])
    assert patients["train"].isdisjoint(patients["test"])
    assert patients["validation"].isdisjoint(patients["test"])
    assert sum(len(frame) for frame in split.values()) == len(rows)


def test_dataset_manifest_rejects_missing_files_and_blank_labels(tmp_path: Path) -> None:
    import pandas as pd
    from ml.dataset import load_manifest

    missing_csv = tmp_path / "missing.csv"
    pd.DataFrame([{"image": "absent.jpg", "label": "nv"}]).to_csv(missing_csv, index=False)
    with pytest.raises(FileNotFoundError, match="missing"):
        load_manifest(missing_csv)

    blank_csv = tmp_path / "blank.csv"
    pd.DataFrame([{"image": "unused.jpg", "label": " "}]).to_csv(blank_csv, index=False)
    with pytest.raises(ValueError, match="empty image path or label"):
        load_manifest(blank_csv)


def test_incompatible_trained_model_bundle_fails_closed(tmp_path: Path) -> None:
    from model_service import ModelService

    weights = tmp_path / "bad.pth"
    torch.save({"state_dict": {"not_a_model_weight": torch.ones(1)}}, weights)
    weights.with_suffix(".classes.json").write_text(
        json.dumps({"architecture": "efficientnet_b0", "classes": ["class_a", "class_b"]}),
        encoding="utf-8",
    )
    service = ModelService(weights)
    assert service.available is False
    assert service.class_names == []
    assert "could not be loaded" in service.message
