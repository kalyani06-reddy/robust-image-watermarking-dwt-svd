import numpy as np

from utils.metrics import psnr, ssim_index, normalized_correlation, bit_error_rate


def test_metrics_are_computable():
    img_a = np.zeros((64, 64), dtype=np.uint8)
    img_b = np.ones((64, 64), dtype=np.uint8) * 10
    wm_a = np.zeros((64, 64), dtype=np.uint8)
    wm_b = np.ones((64, 64), dtype=np.uint8)

    assert psnr(img_a, img_b) > 0
    assert ssim_index(img_a, img_b) >= 0
    assert normalized_correlation(wm_a, wm_b) <= 1
    assert bit_error_rate(wm_a, wm_b) >= 0
