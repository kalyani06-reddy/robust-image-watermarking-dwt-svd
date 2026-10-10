import numpy as np
import pywt

SUPPORTED_SUBBANDS = ("LL", "LH", "HL", "HH")


def normalize_image(image):
    img = np.asarray(image, dtype=np.float64)
    if img.ndim == 3:
        img = np.mean(img, axis=2)
    return img


def dwt_decompose(image, wavelet="haar"):
    img = normalize_image(image)
    ll, (lh, hl, hh) = pywt.dwt2(img, wavelet)
    return {"LL": ll, "LH": lh, "HL": hl, "HH": hh}


def get_subband(image, subband, wavelet="haar"):
    if subband not in SUPPORTED_SUBBANDS:
        raise ValueError(f"Unsupported subband: {subband}")
    return dwt_decompose(image, wavelet)[subband]


def reconstruct_from_subbands(subbands, wavelet="haar"):
    ll = subbands["LL"]
    lh = subbands["LH"]
    hl = subbands["HL"]
    hh = subbands["HH"]
    reconstructed = pywt.idwt2((ll, (lh, hl, hh)), wavelet)
    return np.asarray(reconstructed, dtype=np.float64)
