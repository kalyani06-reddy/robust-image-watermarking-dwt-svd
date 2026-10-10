import cv2
import numpy as np

from algorithms.watermark_extraction import extract_watermark
from utils.metrics import bit_error_rate, normalized_correlation


def apply_jpeg_compression(image, quality):
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), max(1, min(100, int(quality)))]
    _, buffer = cv2.imencode(".jpg", np.uint8(image), encode_param)
    return cv2.imdecode(buffer, cv2.IMREAD_GRAYSCALE)


def apply_gaussian_noise(image, variance):
    noise = np.random.normal(0, np.sqrt(float(variance)), image.shape)
    return np.clip(image.astype(np.float64) + noise, 0, 255).astype(np.uint8)


def apply_salt_pepper_noise(image, density):
    noisy = image.copy().astype(np.float64)
    total = noisy.size
    salt = int(total * float(density) / 2.0)
    pepper = int(total * float(density) / 2.0)
    rng = np.random.default_rng(0)
    coords = rng.choice(total, size=salt + pepper, replace=False)
    for idx in coords[:salt]:
        noisy.flat[idx] = 255
    for idx in coords[salt:]:
        noisy.flat[idx] = 0
    return noisy.astype(np.uint8)


def apply_gaussian_blur(image, kernel_size):
    k = int(kernel_size)
    if k % 2 == 0:
        k += 1
    return cv2.GaussianBlur(image, (k, k), 0)


def apply_resize(image, scale):
    h, w = image.shape
    new_h = max(1, int(h * float(scale)))
    new_w = max(1, int(w * float(scale)))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    restored = cv2.resize(resized, (w, h), interpolation=cv2.INTER_LINEAR)
    return restored


def apply_brightness(image, delta):
    return np.clip(image.astype(np.float64) + float(delta), 0, 255).astype(np.uint8)


def apply_contrast(image, factor):
    return np.clip(image.astype(np.float64) * float(factor), 0, 255).astype(np.uint8)


def apply_crop(image, crop_ratio):
    h, w = image.shape
    crop_h = max(1, int(h * float(crop_ratio)))
    crop_w = max(1, int(w * float(crop_ratio)))
    x0 = (w - crop_w) // 2
    y0 = (h - crop_h) // 2
    cropped = image[y0:y0 + crop_h, x0:x0 + crop_w]
    return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)


def run_robustness_experiment(watermarked_image, original_cover, watermark, attack_specs, **kwargs):
    results = []
    for attack in attack_specs:
        name = attack["name"]
        if name == "jpeg":
            attacked = apply_jpeg_compression(watermarked_image, attack.get("quality", 50))
        elif name == "gaussian_noise":
            attacked = apply_gaussian_noise(watermarked_image, attack.get("variance", 0.01))
        elif name == "salt_pepper":
            attacked = apply_salt_pepper_noise(watermarked_image, attack.get("density", 0.01))
        elif name == "gaussian_blur":
            attacked = apply_gaussian_blur(watermarked_image, attack.get("kernel_size", 5))
        elif name == "resize":
            attacked = apply_resize(watermarked_image, attack.get("scale", 0.8))
        elif name == "brightness":
            attacked = apply_brightness(watermarked_image, attack.get("delta", 20))
        elif name == "contrast":
            attacked = apply_contrast(watermarked_image, attack.get("factor", 1.2))
        elif name == "crop":
            attacked = apply_crop(watermarked_image, attack.get("crop_ratio", 0.8))
        else:
            continue

        extraction = extract_watermark(attacked, original_cover, wavelet=kwargs.get("wavelet", "haar"), level=kwargs.get("level", 1), subband=kwargs.get("subband", "LL"), alpha=kwargs.get("alpha", 0.05), key=kwargs.get("key", ""), original_watermark=watermark)
        results.append({
            "attack": name,
            "attack_params": attack,
            "image": attacked,
            "nc": float(extraction["nc"]),
            "ber": float(extraction["ber"]),
            "extraction_time_ms": float(extraction["extraction_time_ms"]),
        })
    return results
