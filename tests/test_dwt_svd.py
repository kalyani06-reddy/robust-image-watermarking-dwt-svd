import numpy as np

from algorithms.dwt_transform import dwt_decompose, reconstruct_from_subbands
from algorithms.watermark_embedding import embed_watermark


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


def test_multilevel_dwt_reconstruction_preserves_odd_image_shape():
    image = np.random.default_rng(2).random((129, 131)) * 255
    bands = dwt_decompose(image, wavelet='haar', level=2)
    reconstructed = reconstruct_from_subbands(bands, wavelet='haar')
    assert reconstructed.shape == image.shape
    assert np.allclose(reconstructed, image, atol=1e-10)


def test_embedding_resizes_watermark_larger_than_block_capacity():
    cover = np.zeros((32, 32), dtype=np.uint8)
    watermark = np.zeros((300, 300), dtype=np.uint8)
    result = embed_watermark(cover, watermark, level=1, subband='ALL')
    assert result["settings"]["watermark_resized"] is True
    assert result["settings"]["source_watermark_shape"] == [300, 300]
    assert np.prod(result["settings"]["embedded_watermark_shape"]) <= result["settings"]["watermark_capacity"]
