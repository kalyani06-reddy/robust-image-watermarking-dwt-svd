import numpy as np

from algorithms.watermark_embedding import embed_watermark
from algorithms.watermark_extraction import extract_watermark


def test_extraction_without_attack_recovers_watermark():
    cover = (np.random.default_rng(0).random((128, 128)) * 255).astype(np.uint8)
    watermark = (np.random.default_rng(1).random((32, 32)) * 255).astype(np.uint8)

    embedded = embed_watermark(cover, watermark, wavelet='haar', level=1, subband='LL', alpha=0.05, key='secret')
    extracted = extract_watermark(
        embedded['watermarked_image'],
        cover,
        wavelet='haar',
        level=1,
        subband='LL',
        alpha=0.05,
        key='secret',
        original_watermark=watermark,
    )

    assert extracted['extracted_watermark'].shape == watermark.shape
    assert extracted['nc'] > 0.7
    assert extracted['nc'] < 1.0
    assert extracted['ber'] < 0.35
    assert extracted['ber'] > 0.0


def test_extraction_requires_reference_watermark():
    image = np.zeros((128, 128), dtype=np.uint8)
    try:
        extract_watermark(image, image)
    except ValueError as exc:
        assert "Reference watermark" in str(exc)
    else:
        raise AssertionError("Extraction without a reference watermark must fail.")


def test_all_subbands_support_larger_watermark_and_recover_it():
    cover = (np.random.default_rng(3).random((128, 128)) * 255).astype(np.uint8)
    watermark = (np.random.default_rng(4).random((50, 50)) * 255).astype(np.uint8)
    settings = {
        "wavelet": "haar",
        "level": 1,
        "subband": "ALL",
        "alpha": 0.05,
        "key": "all-bands-key",
    }

    embedded = embed_watermark(cover, watermark, **settings)
    extracted = extract_watermark(
        embedded["watermarked_image"],
        cover,
        original_watermark=watermark,
        **settings,
    )

    assert embedded["settings"]["watermark_shape"] == [50, 50]
    assert extracted["extracted_watermark"].shape == watermark.shape
    assert extracted["nc"] > 0.7


def test_single_band_automatically_expands_to_all_subbands():
    cover = (np.random.default_rng(5).random((128, 128)) * 255).astype(np.uint8)
    watermark = (np.random.default_rng(6).random((50, 50)) * 255).astype(np.uint8)
    embedded = embed_watermark(cover, watermark, subband="LL")

    assert embedded["settings"]["subband"] == "ALL"
    assert embedded["settings"]["watermark_resized"] is False


def test_oversized_watermark_is_resized_to_capacity_and_extracts():
    cover = (np.random.default_rng(7).random((64, 64)) * 255).astype(np.uint8)
    watermark = (np.random.default_rng(8).random((200, 200)) * 255).astype(np.uint8)
    settings = {
        "wavelet": "haar",
        "level": 1,
        "subband": "ALL",
        "alpha": 0.05,
        "key": "adaptive-key",
    }

    embedded = embed_watermark(cover, watermark, **settings)
    extracted = extract_watermark(
        embedded["watermarked_image"],
        cover,
        original_watermark=watermark,
        **settings,
    )

    source_shape = embedded["settings"]["source_watermark_shape"]
    encoded_shape = embedded["settings"]["embedded_watermark_shape"]
    capacity = embedded["settings"]["watermark_capacity"]
    assert source_shape == [200, 200]
    assert encoded_shape == extracted["settings"]["embedded_watermark_shape"]
    assert np.prod(encoded_shape) <= capacity
    assert embedded["settings"]["watermark_resized"] is True
    assert extracted["settings"]["watermark_resized"] is True
    assert extracted["extracted_watermark"].shape == watermark.shape
    assert np.isfinite(extracted["nc"])
    assert 0 <= extracted["ber"] <= 1


def test_black_watermark_embeds_and_extracts_without_nc_error():
    cover = np.random.default_rng(11).integers(0, 256, size=(64, 64), dtype=np.uint8)
    watermark = np.zeros((128, 128), dtype=np.uint8)
    settings = {
        "wavelet": "haar",
        "level": 1,
        "subband": "ALL",
        "alpha": 0.05,
        "key": "",
    }
    embedded = embed_watermark(cover, watermark, **settings)
    extracted = extract_watermark(
        embedded["watermarked_image"],
        cover,
        original_watermark=watermark,
        **settings,
    )
    assert extracted["nc"] == 0.0
    assert extracted["ber"] == 0.0
    assert extracted["extracted_watermark"].shape == watermark.shape
