import numpy as np
from skimage.metrics import structural_similarity


def _validated_pair(image_a, image_b, name, value_range=None):
    a = np.asarray(image_a, dtype=np.float64)
    b = np.asarray(image_b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"{name} inputs must have identical dimensions.")
    if a.size == 0 or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError(f"{name} inputs must be non-empty and contain only finite values.")
    if value_range is not None:
        lower, upper = value_range
        if np.min(a) < lower or np.max(a) > upper or np.min(b) < lower or np.max(b) > upper:
            raise ValueError(f"{name} inputs must be in the range {lower} to {upper}.")
    return a, b


def psnr(image_a, image_b):
    img_a, img_b = _validated_pair(image_a, image_b, "PSNR", (0.0, 255.0))
    mse = np.mean((img_a - img_b) ** 2)
    if mse == 0:
        return float("inf")
    return 10.0 * np.log10((255.0 ** 2) / mse)


def ssim_index(image_a, image_b):
    img_a, img_b = _validated_pair(image_a, image_b, "SSIM", (0.0, 255.0))
    if img_a.ndim != 2:
        raise ValueError("SSIM expects two-dimensional grayscale images.")
    return structural_similarity(img_a, img_b, data_range=255.0)


def normalized_correlation(image_a, image_b):
    a, b = _validated_pair(image_a, image_b, "Normalized-correlation", (0.0, 1.0))
    a = a.reshape(-1)
    b = b.reshape(-1)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if np.isclose(denominator, 0.0):
        raise ValueError("Normalized correlation is undefined for a zero watermark.")
    return float(np.clip(np.dot(a, b) / denominator, -1.0, 1.0))


def bit_error_rate(image_a, image_b):
    a, b = _validated_pair(image_a, image_b, "Bit-error-rate", (0.0, 1.0))
    a = a.reshape(-1)
    b = b.reshape(-1)
    threshold_a = a > 0.5
    threshold_b = b > 0.5
    comparisons = np.mean(threshold_a != threshold_b)
    return float(comparisons)
