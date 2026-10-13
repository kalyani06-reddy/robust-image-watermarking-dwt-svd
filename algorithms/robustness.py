import cv2
import numpy as np
import time

from algorithms.watermark_extraction import extract_watermark
from utils.metrics import psnr, ssim_index


def apply_jpeg_compression(image, quality):
    quality = int(quality)
    if not 1 <= quality <= 100:
        raise ValueError("JPEG quality must be between 1 and 100.")
    success, buffer = cv2.imencode(
        ".jpg", np.uint8(image), [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    )
    if not success:
        raise ValueError("JPEG encoding failed.")
    attacked = cv2.imdecode(buffer, cv2.IMREAD_GRAYSCALE)
    if attacked is None:
        raise ValueError("JPEG decoding failed.")
    return attacked


def apply_gaussian_noise(image, variance, seed=0):
    variance = float(variance)
    if not np.isfinite(variance) or variance < 0 or variance > 10000:
        raise ValueError("Gaussian noise variance must be between 0 and 10000.")
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, np.sqrt(variance), image.shape)
    return np.clip(image.astype(np.float64) + noise, 0, 255).astype(np.uint8)


def apply_salt_pepper_noise(image, density, seed=0):
    density = float(density)
    if not np.isfinite(density) or density < 0 or density > 1:
        raise ValueError("Salt-and-pepper density must be between 0 and 1.")
    noisy = image.copy().astype(np.float64)
    total = noisy.size
    salt = int(total * float(density) / 2.0)
    pepper = int(total * float(density) / 2.0)
    rng = np.random.default_rng(seed)
    coords = rng.choice(total, size=salt + pepper, replace=False)
    for idx in coords[:salt]:
        noisy.flat[idx] = 255
    for idx in coords[salt:]:
        noisy.flat[idx] = 0
    return noisy.astype(np.uint8)


def apply_gaussian_blur(image, kernel_size):
    k = int(kernel_size)
    if k < 1 or k > 99:
        raise ValueError("Gaussian blur kernel size must be between 1 and 99.")
    if k % 2 == 0:
        k += 1
    return cv2.GaussianBlur(image, (k, k), 0)


def apply_resize(image, scale):
    scale = float(scale)
    if not np.isfinite(scale) or scale <= 0 or scale > 4:
        raise ValueError("Resize scale must be greater than 0 and at most 4.")
    h, w = image.shape
    new_h = max(1, int(h * scale))
    new_w = max(1, int(w * scale))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    restored = cv2.resize(resized, (w, h), interpolation=cv2.INTER_LINEAR)
    return restored


def apply_brightness(image, delta):
    delta = float(delta)
    if not np.isfinite(delta) or delta < -255 or delta > 255:
        raise ValueError("Brightness delta must be between -255 and 255.")
    return np.clip(image.astype(np.float64) + delta, 0, 255).astype(np.uint8)


def apply_contrast(image, factor):
    factor = float(factor)
    if not np.isfinite(factor) or factor < 0 or factor > 4:
        raise ValueError("Contrast factor must be between 0 and 4.")
    return np.clip(image.astype(np.float64) * factor, 0, 255).astype(np.uint8)


def apply_crop(image, crop_ratio):
    crop_ratio = float(crop_ratio)
    if not np.isfinite(crop_ratio) or crop_ratio <= 0 or crop_ratio > 1:
        raise ValueError("Crop ratio must be greater than 0 and at most 1.")
    h, w = image.shape
    crop_h = max(1, int(h * crop_ratio))
    crop_w = max(1, int(w * crop_ratio))
    x0 = (w - crop_w) // 2
    y0 = (h - crop_h) // 2
    cropped = image[y0:y0 + crop_h, x0:x0 + crop_w]
    return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)


def run_robustness_experiment(watermarked_image, original_cover, watermark, attack_specs, **kwargs):
    if watermark is None:
        raise ValueError("Reference watermark is required for robustness evaluation.")
    if not attack_specs:
        raise ValueError("At least one attack specification is required.")

    watermarked = np.asarray(watermarked_image, dtype=np.uint8)
    results = []
    for attack in attack_specs:
        if not isinstance(attack, dict) or not isinstance(attack.get("name"), str):
            raise ValueError("Each attack must be an object with a name.")
        name = attack["name"]
        if name == "jpeg":
            attacked = apply_jpeg_compression(watermarked_image, attack.get("quality", 50))
        elif name == "gaussian_noise":
            attacked = apply_gaussian_noise(
                watermarked_image,
                attack.get("variance", 25.0),
                attack.get("seed", 0),
            )
        elif name == "salt_pepper":
            attacked = apply_salt_pepper_noise(
                watermarked_image,
                attack.get("density", 0.01),
                attack.get("seed", 0),
            )
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
            raise ValueError(f"Unsupported attack: {name}")

        result = {
            "attack": name,
            "attack_params": attack,
            "attacked_image": attacked,
            "status": "extraction_failed",
            "psnr": float(psnr(watermarked, attacked)),
            "ssim": float(ssim_index(watermarked, attacked)),
            "nc": None,
            "ber": None,
            "extraction_time_ms": None,
        }
        extraction_start = time.perf_counter()
        try:
            extraction = extract_watermark(
                attacked,
                original_cover,
                wavelet=kwargs.get("wavelet", "haar"),
                level=kwargs.get("level", 1),
                subband=kwargs.get("subband", "ALL"),
                alpha=kwargs.get("alpha", 0.05),
                key=kwargs.get("key", ""),
                original_watermark=watermark,
                watermark_type=kwargs.get("watermark_type", "grayscale"),
            )
            result.update(
                status="measured",
                nc=float(extraction["nc"]),
                ber=float(extraction["ber"]),
                extraction_time_ms=float(extraction["extraction_time_ms"]),
            )
        except (ValueError, np.linalg.LinAlgError) as exc:
            result["error"] = str(exc)
            result["extraction_time_ms"] = (time.perf_counter() - extraction_start) * 1000.0
        results.append(result)
    return results
