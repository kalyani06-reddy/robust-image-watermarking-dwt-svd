import time

import cv2
import numpy as np

from algorithms.dwt_transform import dwt_decompose, reconstruct_from_subbands
from algorithms.svd_embedding import (
    prepare_watermark_matrix,
    svd_extract_subband,
    svd_extract_subbands,
)
from algorithms.watermark_payload import fit_watermark_to_subbands
from utils.image_utils import ensure_uint8
from utils.metrics import bit_error_rate, normalized_correlation


def extract_watermark(
    watermarked_image,
    original_cover,
    wavelet="haar",
    level=1,
    subband="LL",
    alpha=0.05,
    key="",
    original_watermark=None,
    watermark_type="grayscale",
):
    if original_cover is None:
        raise ValueError("Original cover image is required for non-blind extraction.")
    if original_watermark is None:
        raise ValueError("Reference watermark is required to restore its dimensions and evaluate recovery.")

    wm = np.asarray(watermarked_image, dtype=np.float64)
    cover = np.asarray(original_cover, dtype=np.float64)
    if wm.ndim == 3:
        wm = np.mean(wm, axis=2)
    if cover.ndim == 3:
        cover = np.mean(cover, axis=2)
    if wm.ndim != 2 or cover.ndim != 2 or wm.size == 0 or cover.size == 0:
        raise ValueError("Watermarked and original cover images must be non-empty grayscale or color arrays.")
    if wm.shape != cover.shape:
        raise ValueError("Watermarked image and original cover must have identical dimensions.")
    if not np.all(np.isfinite(wm)) or not np.all(np.isfinite(cover)):
        raise ValueError("Watermarked and original cover images must contain only finite values.")
    if subband not in ("LL", "LH", "HL", "HH", "ALL"):
        raise ValueError(f"Unsupported subband: {subband}")
    if isinstance(level, bool) or not isinstance(level, (int, np.integer)):
        raise ValueError("Decomposition level must be a positive integer.")

    ref = np.asarray(original_watermark, dtype=np.float64)
    if ref.ndim == 3:
        ref = np.mean(ref, axis=2)
    if ref.ndim != 2 or ref.size == 0 or not np.all(np.isfinite(ref)):
        raise ValueError("Reference watermark must be a non-empty, finite grayscale or color image.")
    if np.min(ref) < 0 or np.max(ref) > 255:
        raise ValueError("Reference watermark pixel values must be in the range 0 to 255.")

    start = time.perf_counter()
    cover_subbands = dwt_decompose(cover, wavelet, level)
    wm_subbands = dwt_decompose(wm, wavelet, level)
    encoded_reference, payload_info = fit_watermark_to_subbands(
        ref, cover_subbands, subband, watermark_type
    )
    subband = payload_info["subband"]
    if subband == "ALL":
        recovered_vector = svd_extract_subbands(
            wm_subbands,
            cover_subbands,
            alpha=alpha,
            key=key,
            watermark_size=encoded_reference.size,
        )
    else:
        cover_subband = cover_subbands[subband]
        wm_subband = wm_subbands[subband]
        recovered_vector = svd_extract_subband(
            wm_subband,
            cover_subband,
            alpha=alpha,
            key=key,
            watermark_size=encoded_reference.size,
        )
    recovered_matrix = recovered_vector.reshape(encoded_reference.shape)
    recovered_small_uint8 = ensure_uint8(recovered_matrix * 255.0)
    if payload_info["resized"]:
        recovered_uint8 = cv2.resize(
            recovered_small_uint8,
            (ref.shape[1], ref.shape[0]),
            interpolation=cv2.INTER_LINEAR,
        )
    else:
        recovered_uint8 = recovered_small_uint8

    target = prepare_watermark_matrix(
        encoded_reference, watermark_type=watermark_type
    )
    nc = normalized_correlation(target, recovered_vector)
    ber = bit_error_rate(target, recovered_vector)

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
            "watermark_shape": list(ref.shape),
            "source_watermark_shape": payload_info["source_shape"],
            "embedded_watermark_shape": payload_info["embedded_shape"],
            "watermark_resized": payload_info["resized"],
            "watermark_capacity": payload_info["capacity"],
            "watermark_type": watermark_type,
        },
    }
