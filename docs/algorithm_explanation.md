# DWT-SVD Watermarking Algorithm

This note describes the block-based, non-blind DWT-SVD method implemented in the application. Extraction requires both the unmodified cover and the same reference watermark used during embedding. Attack resistance is not implied by the algorithm or this description.

## 1. Image preparation and DWT

The application converts cover and watermark images to grayscale values in the 8-bit range. For a cover image \(I \in [0,255]^{H\times W}\), a \(J\)-level, symmetric-boundary 2D wavelet decomposition produces approximation coefficients \(A_J\) and detail bands at each level. The user-selected band is one of LL, LH, HL, or HH at level \(J\). Embedding and extraction must use the same wavelet, level, and band.

Unlike the previous implementation, `level` controls a real multilevel decomposition. The inverse transform restores the original cover dimensions, including for odd-sized images.

## 2. Watermark capacity and embedding

Let the selected band be \(A\). It is partitioned from the top-left into non-overlapping \(2\times2\) blocks \(B_k\). For each block, compute its reduced SVD:

$$
B_k = U_k \operatorname{diag}(\sigma_{k,1}, \sigma_{k,2}) V_k^T,
\qquad \sigma_{k,1} \geq \sigma_{k,2} \geq 0.
$$

The watermark is kept as its original grayscale matrix \(W\), then normalized to \(w_i=W_i/255\) for embedding. In binary mode, pixels are first thresholded at the mean watermark intensity. Each normalized sample is added to the largest singular value of one block:

$$
\sigma'_{k,1} = \sigma_{k,1} + 192\alpha w_{\pi(k)}, \qquad
\sigma'_{k,2} = \sigma_{k,2}.
$$

Here \(\alpha\) is the selected strength and \(\pi\) is the identity ordering unless an optional key is supplied. The key produces a repeatable SHA-256-seeded NumPy permutation; this is reproducible scrambling, not cryptographic protection. The modified block is reconstructed as \(B'_k=U_k\operatorname{diag}(\sigma'_{k,1},\sigma'_{k,2})V_k^T\). Unused blocks and any incomplete border are unchanged. The inverse DWT then produces the watermarked image.

This representation retains every watermark pixel and its width and height; it does not silently resize or subsample. Its capacity is limited to

$$
C = \left\lfloor\frac{r}{2}\right\rfloor
    \left\lfloor\frac{c}{2}\right\rfloor
$$

samples for a selected band of size \(r\times c\). Embedding fails with a clear capacity error if the watermark has more than \(C\) pixels. Increasing capacity by using a deeper level reduces the available band size, so choose cover, watermark, level, band, and strength deliberately.

## 3. Non-blind extraction

Given a watermarked image \(I_w\), the original cover \(I\), and the reference watermark dimensions, the application applies the same DWT settings and extracts the first \(N=H_WW_W\) block coefficients:

$$
\hat{w}_{\pi(k)} =
\operatorname{clip}\left(
\frac{\sigma^{(w)}_{k,1}-\sigma^{(c)}_{k,1}}{192\alpha}, 0, 1
\right).
$$

When a key was used, the same deterministic permutation is inverted. The resulting \(N\) samples are reshaped to the reference watermark's \(H_W\times W_W\) dimensions and converted to an 8-bit image. The original cover, reference watermark, wavelet, level, band, strength, key, and watermark type must match embedding. The reference watermark supplies the dimensions and is also required for meaningful recovery comparison; it is not itself treated as an extracted result.

## 4. Evaluation interpretation and limitations

The additive singular-value difference makes ideal coefficient recovery straightforward, but image reconstruction and 8-bit quantization introduce error. JPEG encoding, filtering, geometric changes, parameter mismatch, and strong attacks can further alter the block coefficients. No resilience is guaranteed. A larger strength generally improves the signal relative to quantization but also increases cover distortion.

The method is non-blind and requires the exact original cover. Its simple row-major block layout has no synchronization or error-correction mechanism, so crop/resize and geometric changes can misalign extraction. A key only permutes samples and is not encryption. The block size is fixed at \(2\times2\); only its largest singular value is modified. Output images are grayscale 8-bit images. Reliability and attack performance must be measured against the actual reference watermark for each experiment.
