from __future__ import annotations

from PIL import Image
from torchvision import transforms

IMAGE_SIZE = 224
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def build_transform(*, training: bool = False, image_size: int = IMAGE_SIZE) -> transforms.Compose:
    """Use one resize/normalization contract; augmentations are training-only."""
    steps: list[object] = []
    if training:
        steps.extend([
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=12),
            transforms.ColorJitter(brightness=0.08, contrast=0.08, saturation=0.05),
        ])
    steps.extend([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    return transforms.Compose(steps)


def preprocess_image(image: Image.Image, *, image_size: int = IMAGE_SIZE):
    """Convert one decoded image into a normalized batched tensor for inference."""
    return build_transform(training=False, image_size=image_size)(image.convert("RGB")).unsqueeze(0)
