from __future__ import annotations

import base64
from io import BytesIO

import cv2
import numpy as np
import torch
from PIL import Image
from torch import nn

from .model import last_convolutional_layer


def gradcam_overlay_data_url(
    model: nn.Module,
    input_tensor: torch.Tensor,
    original_image: Image.Image,
    class_index: int,
) -> str:
    """Return a PNG data URL; hook registration is scoped and always cleaned up."""
    target_layer = last_convolutional_layer(model)
    activations: dict[str, torch.Tensor] = {}
    gradients: dict[str, torch.Tensor] = {}

    def save_activation(_module, _inputs, output: torch.Tensor) -> None:
        activations["value"] = output
        output.register_hook(lambda grad: gradients.__setitem__("value", grad))

    handle = target_layer.register_forward_hook(save_activation)
    try:
        model.zero_grad(set_to_none=True)
        logits = model(input_tensor)
        score = logits[:, class_index].sum()
        score.backward()
        activation = activations.get("value")
        gradient = gradients.get("value")
        if activation is None or gradient is None:
            raise RuntimeError("Grad-CAM did not receive activation and gradient tensors.")
        weights = gradient.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * activation).sum(dim=1, keepdim=True))
        cam = torch.nn.functional.interpolate(
            cam, size=(original_image.height, original_image.width), mode="bilinear", align_corners=False
        )[0, 0]
        cam_np = cam.detach().cpu().numpy()
        max_value = float(cam_np.max())
        if max_value > 0:
            cam_np /= max_value
        heatmap = cv2.applyColorMap(np.uint8(np.clip(cam_np, 0.0, 1.0) * 255), cv2.COLORMAP_JET)
        original = cv2.cvtColor(np.asarray(original_image.convert("RGB")), cv2.COLOR_RGB2BGR)
        blended = cv2.addWeighted(original, 0.58, heatmap, 0.42, 0)
        rgb = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
        buffer = BytesIO()
        Image.fromarray(rgb).save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    finally:
        handle.remove()
        model.zero_grad(set_to_none=True)
