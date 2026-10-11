import time

import numpy as np

from algorithms.dwt_transform import dwt_decompose, reconstruct_from_subbands
from algorithms.svd_embedding import svd_embed_subband
from utils.image_utils import ensure_uint8
from utils.metrics import psnr, ssim_index


def embed_watermark(
    cover_image,
    watermark_image,
    wavelet="haar",
    level=1,
    subband="LL",
    alpha=0.05,
    key="",
    watermark_type="grayscale",
):
    cover = np.asarray(cover_image, dtype=np.float64)
    if cover.ndim == 3:
        cover = np.mean(cover, axis=2)
    if cover.ndim != 2 or cover.size == 0 or not np.all(np.isfinite(cover)):
        raise ValueError("Cover image must be a non-empty, finite grayscale or color array.")
    if np.min(cover) < 0 or np.max(cover) > 255:
        raise ValueError("Cover pixel values must be in the range 0 to 255.")

    watermark = np.asarray(watermark_image, dtype=np.float64)
    if watermark.ndim == 3:
        watermark = np.mean(watermark, axis=2)

    if subband not in ("LL", "LH", "HL", "HH"):
        raise ValueError(f"Unsupported subband: {subband}")
    if isinstance(level, bool) or not isinstance(level, (int, np.integer)):
        raise ValueError("Decomposition level must be a positive integer.")

    start = time.perf_counter()
    subbands = dwt_decompose(cover, wavelet, level)
    selected = subbands[subband]
    watermarked_subband, _, _, _ = svd_embed_subband(
        selected,
        watermark,
        alpha=alpha,
        key=key,
        watermark_type=watermark_type,
    )
    subbands[subband] = watermarked_subband
    watermarked = reconstruct_from_subbands(subbands, wavelet)
    watermarked = watermarked[:cover.shape[0], :cover.shape[1]]
    watermarked_uint8 = ensure_uint8(watermarked)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    metrics = {
        "psnr": float(psnr(cover, watermarked_uint8)),
        "ssim": float(ssim_index(cover, watermarked_uint8)),
        "embedding_time_ms": elapsed_ms,
    }

    return {
        "watermarked_image": watermarked_uint8,
        "cover_image": np.asarray(cover, dtype=np.float64),
        "watermark_matrix": watermark,
        "metrics": metrics,
        "settings": {
            "wavelet": wavelet,
            "level": int(level),
            "subband": subband,
            "alpha": float(alpha),
            "key": bool(key),
            "watermark_shape": list(watermark.shape),
            "watermark_type": watermark_type,
        },
    }
