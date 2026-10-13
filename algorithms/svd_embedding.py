import hashlib

import numpy as np

BLOCK_SIZE = 2
SINGULAR_VALUE_SCALE = 192.0


def _permutation(size, key):
    if not key:
        return np.arange(size)
    digest = hashlib.sha256(str(key).encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return np.random.default_rng(seed).permutation(size)


def scramble_matrix(matrix, key=""):
    values = np.asarray(matrix)
    permutation = _permutation(values.size, key)
    return values.reshape(-1)[permutation].reshape(values.shape), np.argsort(permutation)


def unscramble_matrix(matrix, key="", inverse=None):
    values = np.asarray(matrix)
    if inverse is None:
        inverse = np.argsort(_permutation(values.size, key))
    inverse = np.asarray(inverse, dtype=np.intp)
    if inverse.size != values.size:
        raise ValueError("Permutation size does not match the watermark.")
    return values.reshape(-1)[inverse].reshape(values.shape)


def prepare_watermark_matrix(watermark, target_shape=None, watermark_type="grayscale"):
    watermark = np.asarray(watermark, dtype=np.float64)
    if watermark.ndim == 3:
        watermark = np.mean(watermark, axis=2)
    if watermark.ndim != 2 or watermark.size == 0 or not np.all(np.isfinite(watermark)):
        raise ValueError("Watermark must be a non-empty, finite grayscale or color image.")
    if np.min(watermark) < 0 or np.max(watermark) > 255:
        raise ValueError("Watermark pixel values must be in the range 0 to 255.")
    if watermark_type.lower() == "binary":
        threshold = watermark.mean()
        watermark = (watermark > threshold).astype(np.float64)
    elif watermark_type.lower() == "grayscale":
        watermark = np.clip(watermark / 255.0, 0.0, 1.0)
    else:
        raise ValueError("Watermark type must be 'grayscale' or 'binary'.")

    watermark = watermark.reshape(-1)
    if target_shape is not None:
        capacity = int(np.prod(target_shape)) if isinstance(target_shape, tuple) else int(target_shape)
        if watermark.size > capacity:
            raise ValueError(
                f"Watermark contains {watermark.size} pixels, but the selected "
                f"subband can hold at most {capacity}."
            )
    return watermark.astype(np.float64)


def _block_capacity(subband):
    rows, columns = subband.shape
    return (rows // BLOCK_SIZE) * (columns // BLOCK_SIZE)


def _iter_blocks(subband):
    index = 0
    for top in range(0, subband.shape[0] - BLOCK_SIZE + 1, BLOCK_SIZE):
        for left in range(0, subband.shape[1] - BLOCK_SIZE + 1, BLOCK_SIZE):
            yield index, top, left
            index += 1


def _embed_samples(subband, samples, alpha):
    watermarked = np.asarray(subband, dtype=np.float64).copy()
    singular_values_used = np.empty(len(samples), dtype=np.float64)
    increment = float(alpha) * SINGULAR_VALUE_SCALE
    for slot, top, left in _iter_blocks(watermarked):
        if slot >= len(samples):
            break
        block = watermarked[top:top + BLOCK_SIZE, left:left + BLOCK_SIZE]
        u, singular_values, vt = np.linalg.svd(block, full_matrices=False)
        singular_values_used[slot] = singular_values[0]
        singular_values[0] += increment * samples[slot]
        watermarked[top:top + BLOCK_SIZE, left:left + BLOCK_SIZE] = (
            u @ np.diag(singular_values) @ vt
        )
    return watermarked, singular_values_used


def svd_embed_subband(subband, watermark, alpha=0.05, key="", watermark_type="grayscale"):
    band = np.asarray(subband, dtype=np.float64)
    if band.ndim != 2 or band.size == 0 or not np.all(np.isfinite(band)):
        raise ValueError("Selected DWT subband must be a non-empty finite 2D array.")
    if not np.isfinite(alpha) or alpha <= 0 or alpha > 0.3:
        raise ValueError("Embedding strength must be greater than 0 and at most 0.3.")
    capacity = _block_capacity(band)
    watermark_values = prepare_watermark_matrix(watermark, capacity, watermark_type)
    scrambled, inverse = scramble_matrix(watermark_values, key)
    watermarked, original_singular_values = _embed_samples(band, scrambled, alpha)
    return watermarked, original_singular_values, scrambled, inverse


def svd_embed_subbands(
    subbands,
    watermark,
    alpha=0.05,
    key="",
    watermark_type="grayscale",
):
    band_names = ("LL", "LH", "HL", "HH")
    bands = {name: np.asarray(subbands[name], dtype=np.float64) for name in band_names}
    if any(
        band.ndim != 2 or band.size == 0 or not np.all(np.isfinite(band))
        for band in bands.values()
    ):
        raise ValueError("All selected DWT subbands must be non-empty finite 2D arrays.")
    if not np.isfinite(alpha) or alpha <= 0 or alpha > 0.3:
        raise ValueError("Embedding strength must be greater than 0 and at most 0.3.")
    capacities = {name: _block_capacity(band) for name, band in bands.items()}
    total_capacity = sum(capacities.values())
    watermark_values = prepare_watermark_matrix(
        watermark, total_capacity, watermark_type
    )
    scrambled, inverse = scramble_matrix(watermark_values, key)

    modified_bands = {}
    offset = 0
    for name in band_names:
        count = min(capacities[name], len(scrambled) - offset)
        modified_bands[name], _ = _embed_samples(
            bands[name], scrambled[offset:offset + count], alpha
        )
        offset += count
    return modified_bands, inverse


def _extract_samples(watermarked, original, count, alpha):
    recovered = np.empty(count, dtype=np.float64)
    for slot, top, left in _iter_blocks(original):
        if slot >= count:
            break
        original_block = original[top:top + BLOCK_SIZE, left:left + BLOCK_SIZE]
        watermarked_block = watermarked[top:top + BLOCK_SIZE, left:left + BLOCK_SIZE]
        original_singular = np.linalg.svd(original_block, compute_uv=False)[0]
        watermarked_singular = np.linalg.svd(watermarked_block, compute_uv=False)[0]
        recovered[slot] = (watermarked_singular - original_singular) / (
            float(alpha) * SINGULAR_VALUE_SCALE
        )
    return np.clip(recovered, 0.0, 1.0)


def svd_extract_subband(
    watermarked_subband,
    original_subband,
    alpha=0.05,
    key="",
    inverse=None,
    watermark_size=None,
):
    watermarked = np.asarray(watermarked_subband, dtype=np.float64)
    original = np.asarray(original_subband, dtype=np.float64)
    if watermarked.ndim != 2 or original.ndim != 2 or watermarked.shape != original.shape:
        raise ValueError("Watermarked and original subbands must have identical 2D dimensions.")
    if not np.all(np.isfinite(watermarked)) or not np.all(np.isfinite(original)):
        raise ValueError("DWT subbands must contain only finite values.")
    if not np.isfinite(alpha) or alpha <= 0 or alpha > 0.3:
        raise ValueError("Embedding strength must be greater than 0 and at most 0.3.")
    capacity = _block_capacity(original)
    if watermark_size is None:
        raise ValueError("Reference watermark dimensions are required for extraction.")
    if isinstance(watermark_size, bool) or not isinstance(watermark_size, (int, np.integer)):
        raise ValueError("Watermark size must be a positive integer.")
    if watermark_size < 1 or watermark_size > capacity:
        raise ValueError(
            f"Requested watermark size {watermark_size} exceeds the selected "
            f"subband capacity of {capacity}."
        )

    recovered = _extract_samples(watermarked, original, watermark_size, alpha)
    if key:
        recovered = unscramble_matrix(recovered, key, inverse=inverse)
    return recovered


def svd_extract_subbands(
    watermarked_subbands,
    original_subbands,
    alpha=0.05,
    key="",
    watermark_size=None,
):
    band_names = ("LL", "LH", "HL", "HH")
    watermarked = {
        name: np.asarray(watermarked_subbands[name], dtype=np.float64)
        for name in band_names
    }
    original = {
        name: np.asarray(original_subbands[name], dtype=np.float64)
        for name in band_names
    }
    for name in band_names:
        if (
            watermarked[name].ndim != 2
            or original[name].ndim != 2
            or watermarked[name].shape != original[name].shape
        ):
            raise ValueError(
                f"Watermarked and original {name} subbands must have identical 2D dimensions."
            )
        if not np.all(np.isfinite(watermarked[name])) or not np.all(np.isfinite(original[name])):
            raise ValueError("DWT subbands must contain only finite values.")
    if not np.isfinite(alpha) or alpha <= 0 or alpha > 0.3:
        raise ValueError("Embedding strength must be greater than 0 and at most 0.3.")
    if watermark_size is None:
        raise ValueError("Reference watermark dimensions are required for extraction.")
    if isinstance(watermark_size, bool) or not isinstance(watermark_size, (int, np.integer)):
        raise ValueError("Watermark size must be a positive integer.")
    capacities = {
        name: _block_capacity(original[name])
        for name in band_names
    }
    total_capacity = sum(capacities.values())
    if watermark_size < 1 or watermark_size > total_capacity:
        raise ValueError(
            f"Requested watermark size {watermark_size} exceeds the combined "
            f"DWT subband capacity of {total_capacity}."
        )

    recovered_parts = []
    remaining = watermark_size
    for name in band_names:
        count = min(capacities[name], remaining)
        recovered_parts.append(
            _extract_samples(watermarked[name], original[name], count, alpha)
        )
        remaining -= count
        if remaining == 0:
            break
    recovered = np.concatenate(recovered_parts)
    if key:
        recovered = unscramble_matrix(recovered, key)
    return recovered
