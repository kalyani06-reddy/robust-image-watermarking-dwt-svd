# DWT-SVD Watermarking Algorithm

This note documents the algorithm currently present in the repository. It is a research prototype and should not be interpreted as evidence of measured robustness.

## 1. DWT decomposition

The cover image is converted to grayscale and transformed with one call to `pywt.dwt2`. For a 2D image, the one-level transform provides four subbands:

- **LL:** approximation coefficients
- **LH:** horizontal detail coefficients
- **HL:** vertical detail coefficients
- **HH:** diagonal detail coefficients

The default is Haar and LL. Embedding in a low-frequency band may improve persistence under some processing but can increase visible distortion. Detail bands may be less visible but can be more affected by filtering or compression. These are general trade-offs; this application does not guarantee either outcome. Although a decomposition-level form value exists, current code always applies one-level `dwt2`.

## 2. SVD and embedding

For selected subband $A$, NumPy computes the reduced decomposition:

$$
A = U \operatorname{diag}(s) V^T
$$

The uploaded watermark is converted to grayscale, flattened, and sampled at evenly spaced indices to match the number of singular values. Its samples are normalized to $[0,1]$. With strength $\alpha$, the embedded singular values are:

$$
s' = s + \alpha w
$$

If a key is supplied, a deterministic pseudorandom permutation is applied to $w$ before embedding. The selected band is reconstructed using the original singular vectors:

$$
A' = U \operatorname{diag}(s') V^T
$$

The inverse DWT reconstructs the watermarked image. The watermark is represented as a vector here; its original two-dimensional layout is not retained by this method.

## 3. Non-blind extraction

Extraction requires both the watermarked image and the original cover image. Both are transformed using the same wavelet and selected subband. If $s_w$ and $s$ are their singular-value vectors, the estimate is:

$$
\hat{w} = \operatorname{clip}\left(\frac{s_w-s}{\alpha},0,1\right)
$$

The same key is required when scrambling was used. The current extractor returns the recovered vector; it does not restore the uploaded watermark's original dimensions. This is non-blind extraction and must not be described as blind extraction.

## 4. Key handling

The code uses SHA-256 to derive an integer seed from the key and NumPy's `default_rng` to generate the repeatable permutation. This supports reproducibility, but NumPy's generator is not a cryptographic random-number generator. The permutation should not be described as encryption or cryptographic protection.

## 5. Metrics and attack operators

The project includes PSNR and SSIM utilities for cover/watermarked image comparison and normalized correlation and BER utilities for aligned watermark samples. NC/BER are meaningful only when the original and extracted watermarks are dimensionally aligned and compared sample-by-sample. In the current no-reference extraction branch, NC is calculated by comparing the recovered vector with itself and BER is set to zero; these values do not measure recovery accuracy.

Attack functions exist for JPEG compression, Gaussian noise, salt-and-pepper noise, Gaussian blur, resizing, brightness, contrast, and crop followed by resize. Their presence is not proof of robustness. In particular, the robustness API currently includes NumPy image arrays in JSON results, which requires correction before the full dashboard can return those results reliably.

## 6. Limitations

- The transform is single-level; the level option is not applied.
- The watermark is flattened and sampled to a singular-value-length vector, losing spatial geometry.
- Extraction is non-blind and requires the original cover and matching settings.
- Meaningful recovery metrics require a reference watermark, which the extraction page currently does not upload.
- No validated robustness benchmark or attack-success claim is provided.
- Key-based scrambling is deterministic obfuscation, not cryptographic security.

For the full architecture, setup, test evidence, security notes, and future work, see [academic_project_report.md](academic_project_report.md).
