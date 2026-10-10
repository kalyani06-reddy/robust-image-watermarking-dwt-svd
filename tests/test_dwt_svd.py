import numpy as np
from algorithms.dwt_transform import dwt_decompose, reconstruct_from_subbands


def test_dwt_round_trip_preserves_shape():
    image = np.random.default_rng(0).random((128, 128)) * 255
    bands = dwt_decompose(image, wavelet='haar')
    reconstructed = reconstruct_from_subbands(bands, wavelet='haar')
    assert reconstructed.shape == image.shape


def test_svd_decomposition_is_supported():
    image = np.random.default_rng(1).random((64, 64)) * 255
    bands = dwt_decompose(image, wavelet='haar')
    ll = bands['LL']
    u, s, vt = np.linalg.svd(ll, full_matrices=False)
    recovered = (u @ np.diag(s) @ vt)
    assert recovered.shape == ll.shape
