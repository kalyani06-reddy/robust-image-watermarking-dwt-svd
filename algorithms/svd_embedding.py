import hashlib

import numpy as np


def _seed_from_key(key):
    if not key:
        return 0
    digest = hashlib.sha256(str(key).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def scramble_matrix(matrix, key=""):
    if not key:
        return matrix.copy()
    rng = np.random.default_rng(_seed_from_key(key))
    flat = matrix.reshape(-1)
    permutation = np.arange(flat.size)
    rng.shuffle(permutation)
    inverse = np.empty_like(permutation)
    inverse[permutation] = np.arange(permutation.size)
    return flat[permutation].reshape(matrix.shape), inverse


def unscramble_matrix(matrix, key="", inverse=None):
    if not key:
        return matrix.copy()
    if inverse is None:
        rng = np.random.default_rng(_seed_from_key(key))
        flat = matrix.reshape(-1)
        permutation = np.arange(flat.size)
        rng.shuffle(permutation)
        inverse = np.empty_like(permutation)
        inverse[permutation] = np.arange(permutation.size)
        return flat[inverse].reshape(matrix.shape)
    return matrix.reshape(-1)[inverse].reshape(matrix.shape)


def prepare_watermark_matrix(watermark, target_shape, watermark_type="grayscale"):
    target_size = int(np.prod(target_shape)) if isinstance(target_shape, tuple) else int(target_shape)
    watermark = np.asarray(watermark, dtype=np.float64)
    if watermark.ndim == 3:
        watermark = np.mean(watermark, axis=2)
    watermark = watermark.reshape(-1)

    if watermark.size != target_size:
        if watermark.size == 0:
            watermark = np.zeros(target_size, dtype=np.float64)
        else:
            indices = np.linspace(0, watermark.size - 1, target_size, dtype=int)
            watermark = watermark[indices]

    if watermark_type.lower() == "binary":
        threshold = watermark.mean()
        watermark = (watermark > threshold).astype(np.float64)
    else:
        watermark = np.clip(watermark / 255.0, 0.0, 1.0)

    return watermark.astype(np.float64)[:target_size]


def svd_embed_subband(subband, watermark, alpha=0.05, key=""):
    u, s, vt = np.linalg.svd(subband, full_matrices=False)
    watermark_matrix = prepare_watermark_matrix(watermark, s.shape, watermark_type="grayscale")
    if key:
        scrambled, inverse = scramble_matrix(watermark_matrix, key)
        watermark_matrix = scrambled
    else:
        inverse = None
    updated_s = s + alpha * watermark_matrix
    reconstructed = (u @ np.diag(updated_s) @ vt)
    return reconstructed, s, watermark_matrix, inverse


def svd_extract_subband(watermarked_subband, original_subband, alpha=0.05, key="", inverse=None):
    u_orig, s_orig, vt_orig = np.linalg.svd(original_subband, full_matrices=False)
    u_wm, s_wm, vt_wm = np.linalg.svd(watermarked_subband, full_matrices=False)
    recovered = (s_wm - s_orig) / alpha
    if key:
        recovered = unscramble_matrix(recovered, key, inverse=inverse)
    return np.clip(recovered, 0.0, 1.0)
