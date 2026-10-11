import numpy as np
import pywt

SUPPORTED_SUBBANDS = ("LL", "LH", "HL", "HH")


def normalize_image(image):
    img = np.asarray(image, dtype=np.float64)
    if img.ndim == 3:
        img = np.mean(img, axis=2)
    if img.ndim != 2 or img.size == 0 or not np.all(np.isfinite(img)):
        raise ValueError("Image must be a non-empty, finite grayscale or color array.")
    return img


def _validate_decomposition(image, wavelet, level):
    img = normalize_image(image)
    try:
        wavelet_obj = pywt.Wavelet(wavelet)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unsupported wavelet: {wavelet}") from exc
    if isinstance(level, bool) or not isinstance(level, (int, np.integer)) or level < 1:
        raise ValueError("Decomposition level must be a positive integer.")
    max_level = pywt.dwtn_max_level(img.shape, wavelet_obj)
    if level > max_level:
        raise ValueError(
            f"Decomposition level {level} is too high for image dimensions "
            f"{img.shape}; maximum supported level is {max_level}."
        )
    return img, wavelet_obj


def dwt_decompose(image, wavelet="haar", level=1):
    img, wavelet_obj = _validate_decomposition(image, wavelet, level)
    coefficients = pywt.wavedec2(img, wavelet_obj, level=level, mode="symmetric")
    lh, hl, hh = coefficients[1]
    return {
        "LL": coefficients[0],
        "LH": lh,
        "HL": hl,
        "HH": hh,
        "_details": coefficients[2:],
        "_shape": img.shape,
        "_mode": "symmetric",
    }


def get_subband(image, subband, wavelet="haar", level=1):
    if subband not in SUPPORTED_SUBBANDS:
        raise ValueError(f"Unsupported subband: {subband}")
    return dwt_decompose(image, wavelet, level)[subband]


def reconstruct_from_subbands(subbands, wavelet="haar"):
    try:
        coefficients = [
            subbands["LL"],
            (subbands["LH"], subbands["HL"], subbands["HH"]),
            *subbands["_details"],
        ]
    except KeyError as exc:
        raise ValueError("DWT coefficient data is incomplete.") from exc
    reconstructed = pywt.waverec2(
        coefficients,
        wavelet,
        mode=subbands.get("_mode", "symmetric"),
    )
    shape = subbands.get("_shape")
    if shape is not None:
        reconstructed = reconstructed[:shape[0], :shape[1]]
    return np.asarray(reconstructed, dtype=np.float64)
