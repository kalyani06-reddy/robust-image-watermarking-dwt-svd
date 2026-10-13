import numpy as np
import pytest

from utils.metrics import psnr, ssim_index, normalized_correlation, bit_error_rate


def test_metrics_are_computable():
    img_a = np.zeros((64, 64), dtype=np.uint8)
    img_b = np.ones((64, 64), dtype=np.uint8) * 10
    wm_a = np.tile(np.array([0.0, 1.0]), (32, 32))
    wm_b = np.tile(np.array([0.0, 0.8]), (32, 32))

    assert psnr(img_a, img_b) > 0
    assert ssim_index(img_a, img_b) >= 0
    assert normalized_correlation(wm_a, wm_b) <= 1
    assert bit_error_rate(wm_a, wm_b) >= 0


def test_watermark_metrics_reject_mismatched_dimensions():
    with pytest.raises(ValueError, match="identical dimensions"):
        normalized_correlation(np.zeros((2, 3)), np.zeros((6,)))
    with pytest.raises(ValueError, match="identical dimensions"):
        bit_error_rate(np.zeros((2, 3)), np.zeros((6,)))


def test_ber_rejects_values_outside_normalized_range():
    with pytest.raises(ValueError, match="range 0.0 to 1.0"):
        bit_error_rate(np.array([0.0, 2.0]), np.array([0.0, 1.0]))


def test_nc_handles_zero_watermarks_without_fabricating_similarity():
    zero = np.zeros((4,))
    nonzero = np.array([0.0, 1.0, 0.0, 1.0])
    assert normalized_correlation(zero, zero) == 1.0
    assert normalized_correlation(zero, nonzero) == 0.0
    assert normalized_correlation(nonzero, zero) == 0.0


def test_nc_zero_reference_does_not_score_nonzero_extraction_as_perfect():
    reference = np.zeros((2, 2))
    recovered = np.array([[0.0, 0.1], [0.0, 0.0]])
    assert normalized_correlation(reference, recovered) == 0.0
