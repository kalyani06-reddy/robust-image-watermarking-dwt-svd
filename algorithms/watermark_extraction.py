import time

import numpy as np

from algorithms.dwt_transform import dwt_decompose, reconstruct_from_subbands
from algorithms.svd_embedding import svd_extract_subband
from utils.image_utils import ensure_uint8
from utils.metrics import bit_error_rate, normalized_correlation


def extract_watermark(watermarked_image, original_cover, wavelet="haar", level=1, subband="LL", alpha=0.05, key="", original_watermark=None):
    if original_cover is None:
        raise ValueError("Original cover image is required for non-blind extraction.")

    wm = np.asarray(watermarked_image, dtype=np.float64)
    cover = np.asarray(original_cover, dtype=np.float64)
    if wm.ndim == 3:
        wm = np.mean(wm, axis=2)
    if cover.ndim == 3:
        cover = np.mean(cover, axis=2)

    start = time.perf_counter()
    cover_subbands = dwt_decompose(cover, wavelet)
    wm_subbands = dwt_decompose(wm, wavelet)
    cover_subband = cover_subbands[subband]
    wm_subband = wm_subbands[subband]

    recovered_matrix = svd_extract_subband(wm_subband, cover_subband, alpha=alpha, key=key)
    recovered_uint8 = ensure_uint8(recovered_matrix)

    if original_watermark is not None:
        ref = np.asarray(original_watermark, dtype=np.float64)
        if ref.ndim == 3:
            ref = np.mean(ref, axis=2)
        ref = ref.reshape(-1)
        recovered_vector = np.asarray(recovered_matrix, dtype=np.float64).reshape(-1)
        if ref.size != recovered_vector.size:
            indices = np.linspace(0, ref.size - 1, recovered_vector.size, dtype=int)
            ref = ref[indices]
        target = np.clip(ref / 255.0, 0.0, 1.0)
        nc = normalized_correlation(target, recovered_vector)
        ber = bit_error_rate(target, recovered_vector)
    else:
        recovered_vector = np.asarray(recovered_matrix, dtype=np.float64).reshape(-1)
        nc = normalized_correlation(recovered_vector, recovered_vector)
        ber = 0.0

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return {
        "extracted_watermark": recovered_uint8,
        "nc": float(nc),
        "ber": float(ber),
        "extraction_time_ms": elapsed_ms,
        "settings": {
            "wavelet": wavelet,
            "level": int(level),
            "subband": subband,
            "alpha": float(alpha),
            "key": bool(key),
        },
    }
