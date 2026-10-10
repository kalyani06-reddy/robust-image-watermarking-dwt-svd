import time

import numpy as np

from algorithms.dwt_transform import dwt_decompose, reconstruct_from_subbands
from algorithms.svd_embedding import svd_embed_subband
from utils.image_utils import ensure_uint8
from utils.metrics import psnr, ssim_index


def embed_watermark(cover_image, watermark_image, wavelet="haar", level=1, subband="LL", alpha=0.05, key=""):
    cover = np.asarray(cover_image, dtype=np.float64)
    if cover.ndim == 3:
        cover = np.mean(cover, axis=2)

    watermark = np.asarray(watermark_image, dtype=np.float64)
    if watermark.ndim == 3:
        watermark = np.mean(watermark, axis=2)

    start = time.perf_counter()
    subbands = dwt_decompose(cover, wavelet)
    selected = subbands[subband]
    watermarked_subband, _, _, inverse = svd_embed_subband(selected, watermark, alpha=alpha, key=key)
    subbands[subband] = watermarked_subband
    watermarked = reconstruct_from_subbands(subbands, wavelet)
    watermarked_uint8 = ensure_uint8(watermarked)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    metrics = {
        "psnr": float(psnr(cover, watermarked)),
        "ssim": float(ssim_index(cover, watermarked)),
        "nc": 0.0,
        "ber": 0.0,
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
            "scramble_inverse": inverse,
        },
    }
