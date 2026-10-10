import numpy as np
from skimage.metrics import structural_similarity


def psnr(image_a, image_b):
    img_a = np.asarray(image_a, dtype=np.float64)
    img_b = np.asarray(image_b, dtype=np.float64)
    mse = np.mean((img_a - img_b) ** 2)
    if mse == 0:
        return float("inf")
    max_pixel = 255.0
    return 10.0 * np.log10((max_pixel ** 2) / mse)


def ssim_index(image_a, image_b):
    img_a = np.asarray(image_a, dtype=np.float64)
    img_b = np.asarray(image_b, dtype=np.float64)
    data_range = float(np.max([np.max(img_a), np.max(img_b), 1.0]))
    return structural_similarity(img_a, img_b, data_range=data_range)


def normalized_correlation(image_a, image_b):
    a = np.asarray(image_a, dtype=np.float64).reshape(-1)
    b = np.asarray(image_b, dtype=np.float64).reshape(-1)
    if a.size != b.size:
        n = min(a.size, b.size)
        a = a[:n]
        b = b[:n]
    a_mean = np.mean(a)
    b_mean = np.mean(b)
    a_centered = a - a_mean
    b_centered = b - b_mean
    numerator = np.dot(a_centered, b_centered)
    denominator = np.linalg.norm(a_centered) * np.linalg.norm(b_centered)
    if np.isclose(denominator, 0.0):
        return 0.0
    return float(numerator / denominator)


def bit_error_rate(image_a, image_b):
    a = np.asarray(image_a, dtype=np.float64).reshape(-1)
    b = np.asarray(image_b, dtype=np.float64).reshape(-1)
    if a.size != b.size:
        n = min(a.size, b.size)
        a = a[:n]
        b = b[:n]
    threshold_a = a > 0.5
    threshold_b = b > 0.5
    comparisons = np.mean(threshold_a != threshold_b)
    return float(comparisons)
