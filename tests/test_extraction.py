import numpy as np

from algorithms.watermark_embedding import embed_watermark
from algorithms.watermark_extraction import extract_watermark


def test_extraction_without_attack_recovers_watermark():
    cover = (np.random.default_rng(0).random((128, 128)) * 255).astype(np.uint8)
    watermark = (np.random.default_rng(1).random((64, 64)) * 255).astype(np.uint8)

    embedded = embed_watermark(cover, watermark, wavelet='haar', level=1, subband='LL', alpha=0.05, key='secret')
    extracted = extract_watermark(embedded['watermarked_image'], cover, wavelet='haar', level=1, subband='LL', alpha=0.05, key='secret')

    assert extracted['nc'] > 0.7
    assert extracted['ber'] < 0.35
