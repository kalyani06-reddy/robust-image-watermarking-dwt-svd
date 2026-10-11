import numpy as np
from PIL import Image

from algorithms.watermark_embedding import embed_watermark


def test_embedding_preserves_shape_and_returns_image():
    cover = np.zeros((256, 256), dtype=np.uint8)
    cover[20:220, 20:220] = 200
    watermark = np.ones((64, 64), dtype=np.uint8) * 255

    result = embed_watermark(cover, watermark, wavelet='haar', level=1, subband='LL', alpha=0.05, key='demo-key')

    assert result['watermarked_image'].shape == cover.shape
    assert result['settings']['watermark_shape'] == [64, 64]
    assert result['metrics']['psnr'] > 20
    assert result['metrics']['ssim'] > 0.85
