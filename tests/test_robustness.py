import numpy as np
import pytest

from algorithms.robustness import run_robustness_experiment
from algorithms.watermark_embedding import embed_watermark


def test_robustness_experiment_returns_results():
    cover = np.zeros((128, 128), dtype=np.uint8)
    cover[20:110, 20:110] = 200
    watermark = np.tile(np.array([0, 255], dtype=np.uint8), (16, 16))
    watermarked = embed_watermark(
        cover, watermark, wavelet='haar', level=1, subband='LL', alpha=0.05, key='demo'
    )['watermarked_image']

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
    assert results[0]["status"] == "measured"
    assert results[0]["nc"] is not None
    assert results[0]["ber"] is not None
    assert results[1]["status"] == "measured"
    assert results[1]["nc"] is not None
    assert results[1]["ber"] is not None
    assert all(result["psnr"] > 0 and result["ssim"] <= 1 for result in results)
    assert all(result["extraction_time_ms"] >= 0 for result in results)


def test_robustness_records_extraction_failure_without_scores():
    cover = np.zeros((128, 128), dtype=np.uint8)
    watermark = np.tile(np.array([0, 255], dtype=np.uint8), (16, 16))
    watermarked = embed_watermark(cover, watermark)['watermarked_image']
    results = run_robustness_experiment(
        watermarked,
        cover,
        watermark,
        [{"name": "brightness", "delta": 1}],
        alpha=0,
    )
    assert results[0]["status"] == "extraction_failed"
    assert results[0]["nc"] is None
    assert results[0]["ber"] is None
    assert results[0]["error"]


def test_robustness_rejects_missing_reference_watermark():
    image = np.zeros((128, 128), dtype=np.uint8)
    with pytest.raises(ValueError, match="Reference watermark is required"):
        run_robustness_experiment(image, image, None, [{"name": "jpeg", "quality": 80}])
