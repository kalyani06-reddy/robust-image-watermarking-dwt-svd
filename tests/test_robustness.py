import numpy as np

from algorithms.robustness import run_robustness_experiment


def test_robustness_experiment_returns_results():
    cover = np.zeros((128, 128), dtype=np.uint8)
    cover[20:110, 20:110] = 200
    watermark = np.ones((32, 32), dtype=np.uint8) * 255
    watermarked = cover.copy()

    results = run_robustness_experiment(
        watermarked,
        cover,
        watermark,
        [{"name": "jpeg", "quality": 80}, {"name": "brightness", "delta": 20}],
        wavelet="haar",
        level=1,
        subband="LL",
        alpha=0.05,
        key="demo",
    )

    assert len(results) == 2
    assert all("nc" in result for result in results)
    assert all("ber" in result for result in results)
