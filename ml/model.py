from __future__ import annotations

from torch import nn
from torchvision.models import (
    ConvNeXt_Tiny_Weights,
    DenseNet121_Weights,
    EfficientNet_B0_Weights,
    convnext_tiny,
    densenet121,
    efficientnet_b0,
)


ARCHITECTURES = {"efficientnet_b0", "convnext_tiny", "densenet121"}


def build_classifier(architecture: str, num_classes: int, *, pretrained: bool = False) -> nn.Module:
    if num_classes < 2:
        raise ValueError("Classification requires at least two configured classes.")
    name = architecture.lower()
    if name == "efficientnet_b0":
        model = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT if pretrained else None)
        input_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(input_features, num_classes)
    elif name == "convnext_tiny":
        model = convnext_tiny(weights=ConvNeXt_Tiny_Weights.DEFAULT if pretrained else None)
        input_features = model.classifier[2].in_features
        model.classifier[2] = nn.Linear(input_features, num_classes)
    elif name == "densenet121":
        model = densenet121(weights=DenseNet121_Weights.DEFAULT if pretrained else None)
        input_features = model.classifier.in_features
        model.classifier = nn.Linear(input_features, num_classes)
    else:
        raise ValueError(f"Unsupported architecture '{architecture}'. Choose from {sorted(ARCHITECTURES)}.")
    return model


def last_convolutional_layer(model: nn.Module) -> nn.Module:
    candidates = [module for module in model.modules() if isinstance(module, nn.Conv2d)]
    if not candidates:
        raise ValueError("The selected model has no convolutional layer for Grad-CAM.")
    return candidates[-1]
