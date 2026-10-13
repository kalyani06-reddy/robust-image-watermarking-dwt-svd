import numpy as np
import pytest

from algorithms.strength_tuning import tune_watermark_strength


def test_strength_tuner_measures_candidates_and_returns_best_embedding():
    rng = np.random.default_rng(14)
    cover = rng.integers(0, 256, size=(64, 64), dtype=np.uint8)
    watermark = rng.integers(0, 256, size=(8, 8), dtype=np.uint8)

    result = tune_watermark_strength(
        cover,
        watermark,
        [{"name": "brightness", "delta": 1}],
        psnr_floor=0,
        strengths=[0.03, 0.08],
        wavelet="haar",
        level=1,
        subband="ALL",
    )

    assert [trial["strength"] for trial in result["trials"]] == [0.03, 0.08]
    assert all(trial["status"] == "measured" for trial in result["trials"])
    assert all(trial["measured_attacks"] == 1 for trial in result["trials"])
    assert result["recommended_strength"] in (0.03, 0.08)
    assert result["recommended_embedding"]["watermarked_image"].shape == cover.shape


def test_strength_tuner_excludes_candidates_below_psnr_floor():
    cover = np.full((64, 64), 128, dtype=np.uint8)
    watermark = np.full((8, 8), 255, dtype=np.uint8)

    result = tune_watermark_strength(
        cover,
        watermark,
        [{"name": "brightness", "delta": 1}],
        psnr_floor=100,
        strengths=[0.05],
        wavelet="haar",
        level=1,
        subband="ALL",
    )

    assert result["trials"][0]["status"] == "below_psnr"
    assert result["trials"][0]["mean_nc"] is None
    assert result["recommended_strength"] is None
    assert result["recommended_embedding"] is None


def test_strength_tuner_validates_search_inputs():
    image = np.zeros((32, 32), dtype=np.uint8)
    watermark = np.zeros((4, 4), dtype=np.uint8)

    with pytest.raises(ValueError, match="At least one attack"):
        tune_watermark_strength(image, watermark, [], strengths=[0.05])
    with pytest.raises(ValueError, match="unique"):
        tune_watermark_strength(
            image,
            watermark,
            [{"name": "brightness", "delta": 1}],
            strengths=[0.05, 0.05],
        )
