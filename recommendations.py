from __future__ import annotations

import re
from typing import Any


DISCLAIMER = (
    "SkinSight is an academic image-screening prototype, not a medical diagnostic system. "
    "Image-based model output can be wrong, cannot recommend personal treatment, and must not replace "
    "assessment by a qualified clinician."
)

COMMON_GUIDANCE = [
    "Use gentle cleansing and moisturize if your skin feels dry or irritated.",
    "Protect exposed skin from sun with shade, clothing, and broad-spectrum sunscreen.",
]
CARE_NOTICE = (
    "Seek professional assessment for a lesion that is changing, bleeding, painful, persistent, "
    "or concerning to you. Do not delay care because of an image-model result."
)
HIGH_CONCERN_CARE_NOTICE = (
    "This model label is associated with a condition that needs professional assessment, but it is not "
    "a diagnosis. Please arrange prompt review with a qualified dermatologist. Do not start treatment "
    "or delay care based on this image-model result."
)
LIMITATION = (
    "This educational description reflects a model label, not a diagnosis. SkinSight cannot recommend "
    "personal treatment. "
    "Do not start treatment or delay care based on this result. Dermoscopic research images do not "
    "guarantee reliable results on ordinary smartphone photos."
)

EDUCATIONAL_CONTENT: dict[str, dict[str, Any]] = {
    "akiec": {
        "title": "Actinic keratosis / intraepithelial carcinoma model label",
        "information": "This image category can include lesions that need clinical assessment. An image model cannot confirm what a spot is; a qualified clinician must assess it.",
    },
    "bcc": {
        "title": "Basal cell carcinoma (BCC) model label",
        "information": "This is an image-model category, not a finding about your health. Only a qualified clinician can assess an individual lesion.",
    },
    "bkl": {
        "title": "Benign keratosis-like (BKL) model label",
        "information": "A model label cannot establish that a spot is benign. Similar-looking skin changes can have different causes and may need professional assessment.",
    },
    "df": {
        "title": "Dermatofibroma (DF) model label",
        "information": "This is a visual category only; the prototype cannot confirm the nature of a skin lesion.",
    },
    "mel": {
        "title": "Melanoma model label",
        "information": "This model label is not a diagnosis, but it should be checked by a qualified dermatologist. Do not rely on this prototype to decide whether a lesion is safe.",
    },
    "nv": {
        "title": "Melanocytic nevus (mole) model label",
        "information": "A model label cannot determine whether an individual mole is harmless. Ask a qualified clinician about a spot that is new, changing, or concerning.",
    },
    "vasc": {
        "title": "Vascular lesion model label",
        "information": "This is a visual category only; the prototype cannot identify or confirm the cause of a skin change.",
    },
    "atopic_dermatitis": {
        "title": "Atopic dermatitis model label",
        "information": "This is an image-model category only. Rashes can look similar but have different causes, so a clinician is needed to confirm a condition and discuss treatment.",
    },
    "eczema": {
        "title": "Eczema model label",
        "information": "This is an image-model category only. Rashes can look similar but have different causes, so a clinician is needed to confirm a condition and discuss treatment.",
    },
    "psoriasis": {
        "title": "Psoriasis model label",
        "information": "This is an image-model category only. A clinician must assess the skin and confirm a condition before treatment is chosen.",
    },
    "seborrheic_keratoses": {
        "title": "Seborrheic keratosis model label",
        "information": "A model label cannot confirm that a growth is harmless. Have a new, changing, or concerning spot assessed by a qualified clinician.",
    },
    "tinea": {
        "title": "Fungal-infection model label",
        "information": "This is an image-model category only. Different skin conditions can look similar; a clinician or pharmacist can advise on appropriate care.",
    },
    "warts": {
        "title": "Viral skin-condition model label",
        "information": "This is an image-model category only. A qualified clinician can confirm the cause and discuss suitable care.",
    },
    "scc": {
        "title": "Squamous cell carcinoma (SCC) model label",
        "information": "This model label is not a diagnosis, but it should be checked by a qualified dermatologist. Do not rely on this prototype to decide whether a lesion is safe.",
    },
}

CATEGORY_ALIASES = {
    "akiec": "akiec",
    "actinic keratosis": "akiec",
    "actinic keratosis intraepithelial carcinoma": "akiec",
    "actinic keratoses": "akiec",
    "bcc": "bcc",
    "basal cell carcinoma": "bcc",
    "basal cell carcinoma bcc": "bcc",
    "bkl": "bkl",
    "benign keratosis like lesions bkl": "bkl",
    "df": "df",
    "dermatofibroma": "df",
    "dermatofibroma df": "df",
    "mel": "mel",
    "melanoma": "mel",
    "nv": "nv",
    "melanocytic nevi nv": "nv",
    "melanocytic nevus": "nv",
    "mole": "nv",
    "vasc": "vasc",
    "vascular lesion": "vasc",
    "atopic dermatitis": "atopic_dermatitis",
    "eczema": "eczema",
    "psoriasis": "psoriasis",
    "psoriasis pictures lichen planus and related diseases": "psoriasis",
    "seborrheic keratoses and other benign tumors": "seborrheic_keratoses",
    "seborrheic keratosis": "seborrheic_keratoses",
    "tinea": "tinea",
    "tinea ringworm candidiasis and other fungal infections": "tinea",
    "squamous cell carcinoma": "scc",
    "squamous cell carcinoma scc": "scc",
    "scc": "scc",
    "warts molluscum and other viral infections": "warts",
    "warts": "warts",
}

HIGH_CONCERN_CATEGORIES = {"akiec", "bcc", "mel", "scc"}


def recommendation_for(category: str | None) -> dict[str, Any]:
    normalized = re.sub(r"[^a-z0-9]+", " ", category.lower()).strip() if category else ""
    key = CATEGORY_ALIASES.get(normalized, "")
    content = EDUCATIONAL_CONTENT.get(key)
    if content is None:
        title = "General skin-care information"
        information = (
            "No category-specific educational content is configured. A visual class, when available, "
            "is not a medical diagnosis and may not represent the cause of a skin change."
        )
    else:
        title = content["title"]
        information = content["information"]
    return {
        "title": title,
        "information": information,
        "general_guidance": list(COMMON_GUIDANCE),
        "care_notice": HIGH_CONCERN_CARE_NOTICE if key in HIGH_CONCERN_CATEGORIES else CARE_NOTICE,
        "limitation": LIMITATION,
    }
