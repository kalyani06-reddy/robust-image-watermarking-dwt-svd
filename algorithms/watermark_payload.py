import cv2
import numpy as np

from algorithms.svd_embedding import _block_capacity

SUBBANDS = ("LL", "LH", "HL", "HH")


def fit_watermark_to_subbands(watermark, subbands, subband, watermark_type):
    image = np.asarray(watermark, dtype=np.float64)
    if image.ndim == 3:
        image = np.mean(image, axis=2)
    if image.ndim != 2 or image.size == 0 or not np.all(np.isfinite(image)):
        raise ValueError("Watermark must be a non-empty, finite grayscale or color image.")
    if np.min(image) < 0 or np.max(image) > 255:
        raise ValueError("Watermark pixel values must be in the range 0 to 255.")

    original_shape = image.shape
    capacities = {name: _block_capacity(subbands[name]) for name in SUBBANDS}
    all_capacity = sum(capacities.values())
    if subband not in (*SUBBANDS, "ALL"):
        raise ValueError(f"Unsupported subband: {subband}")

    selected_subband = subband
    capacity = all_capacity if subband == "ALL" else capacities[subband]
    if image.size > capacity and subband != "ALL":
        selected_subband = "ALL"
        capacity = all_capacity

    if capacity < 1:
        raise ValueError("The cover image is too small to hold watermark samples.")

    if image.size > capacity:
        scale = np.sqrt(capacity / image.size)
        height = max(1, min(image.shape[0], int(image.shape[0] * scale)))
        width = max(1, min(image.shape[1], capacity // height))
        while height * width > capacity:
            if width >= height:
                width -= 1
            else:
                height -= 1
        image = cv2.resize(
            image.astype(np.float32),
            (width, height),
            interpolation=cv2.INTER_AREA,
        ).astype(np.float64)

    return image, {
        "source_shape": list(original_shape),
        "embedded_shape": list(image.shape),
        "resized": list(image.shape) != list(original_shape),
        "subband": selected_subband,
        "capacity": capacity,
    }
