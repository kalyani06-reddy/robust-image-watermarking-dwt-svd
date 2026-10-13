# DWT-SVD Watermarking Algorithm

This note describes the block-based, non-blind DWT-SVD method implemented in the application. Extraction requires both the unmodified cover and the same reference watermark used during embedding. Attack resistance is not implied by the algorithm or this description.

## 1. Image preparation and DWT

The application converts cover and watermark images to grayscale values in the 8-bit range. For a cover image \(I \in [0,255]^{H\times W}\), a \(J\)-level, symmetric-boundary 2D wavelet decomposition produces approximation coefficients \(A_J\) and detail bands at each level. Embedding can use one user-selected band (LL, LH, HL, or HH) or all four bands at level \(J\). Embedding and extraction must use the same wavelet, level, and band selection.

Unlike the previous implementation, `level` controls a real multilevel decomposition. The inverse transform restores the original cover dimensions, including for odd-sized images.

## 2. Watermark capacity and embedding

Let the selected band be \(A\). It is partitioned from the top-left into non-overlapping \(2\times2\) blocks \(B_k\). For each block, compute its reduced SVD:

$$
B_k = U_k \operatorname{diag}(\sigma_{k,1}, \sigma_{k,2}) V_k^T,
\qquad \sigma_{k,1} \geq \sigma_{k,2} \geq 0.
$$

The source watermark \(W\) is retained at its original size for reference and display. If it exceeds capacity, it is downscaled with area interpolation to an effective payload \(W_e\); only \(W_e\) can be embedded. Effective grayscale samples are normalized as \(w_i=W_{e,i}/255\). In binary mode, effective samples are thresholded at their mean intensity. Each normalized sample is added to the largest singular value of one block:

$$
\sigma'_{k,1} = \sigma_{k,1} + 192\alpha w_{\pi(k)}, \qquad
\sigma'_{k,2} = \sigma_{k,2}.
$$

Here \(\alpha\) is the selected strength and \(\pi\) is the identity ordering unless an optional key is supplied. The key produces a repeatable SHA-256-seeded NumPy permutation; this is reproducible scrambling, not cryptographic protection. The modified block is reconstructed as \(B'_k=U_k\operatorname{diag}(\sigma'_{k,1},\sigma'_{k,2})V_k^T\). Unused blocks and any incomplete border are unchanged. The inverse DWT then produces the watermarked image.

The original watermark dimensions are retained as metadata. The embedded representation is automatically resized when it exceeds coefficient capacity; such resizing is lossy and fine details cannot be reconstructed. The capacity of one selected band is

$$
C = \left\lfloor\frac{r}{2}\right\rfloor
    \left\lfloor\frac{c}{2}\right\rfloor
$$

samples for a selected band of size \(r\times c\). If a single selected band is too small, the app automatically selects **ALL**. If the watermark is still larger than the combined capacity, it is downscaled with area interpolation to no more than that capacity. Increasing capacity by using a deeper level reduces the available band size, so choose cover, watermark, level, band, and strength deliberately.

With **ALL**, the same block method is applied first to LL, then LH, HL, and HH. The scrambled watermark vector is split in that order, and extraction concatenates estimates in the same order before undoing the key permutation. The combined capacity is the sum of each band's block capacity:

$$
C_{\mathrm{all}}=\sum_{b\in\{\mathrm{LL,LH,HL,HH}\}}
\left\lfloor\frac{r_b}{2}\right\rfloor
\left\lfloor\frac{c_b}{2}\right\rfloor.
$$

For a usual level-1 transform with equal-sized bands this is four times a single-band capacity. **ALL** is the default in the UI to accommodate larger watermarks. Selecting one band remains useful when the watermark fits that band's lower capacity; otherwise the app falls back to **ALL**. If needed, the fitted watermark dimensions and capacity are returned with embedding results. Extraction applies the same fit to the reference, compares against that representable payload, and enlarges the extracted image to the original dimensions for display. Enlargement does not restore information discarded by downscaling.

## 3. Non-blind extraction

Given a watermarked image \(I_w\), the original cover \(I\), and the reference watermark dimensions, the application applies the same DWT settings and extracts the first \(N=H_WW_W\) block coefficients:

$$
\hat{w}_{\pi(k)} =
\operatorname{clip}\left(
\frac{\sigma^{(w)}_{k,1}-\sigma^{(c)}_{k,1}}{192\alpha}, 0, 1
\right).
$$

When a key was used, the same deterministic permutation is inverted. The resulting samples are reshaped to the effective embedded dimensions for reference-based metrics. The rendered extraction is enlarged to the source watermark's \(H_W\times W_W\) dimensions when fitting was needed. The original cover, reference watermark, wavelet, level, band selection, strength, key, and watermark type must match embedding. The reference watermark supplies the original dimensions and the comparison source; it is not itself treated as an extracted result.

## 4. Evaluation interpretation and limitations

The additive singular-value difference makes ideal coefficient recovery straightforward, but image reconstruction and 8-bit quantization introduce error. JPEG encoding, filtering, geometric changes, parameter mismatch, and strong attacks can further alter the block coefficients. No resilience is guaranteed. A larger strength generally improves the signal relative to quantization but also increases cover distortion.

The method is non-blind and requires the exact original cover. Its simple row-major block layout has no synchronization or error-correction mechanism, so crop/resize and geometric changes can misalign extraction. A key only permutes samples and is not encryption. The block size is fixed at \(2\times2\); only its largest singular value is modified. Output images are grayscale 8-bit images. For NC, two all-zero arrays are assigned 1 (exact zero-payload match); if only one is zero, NC is 0. This convention prevents black watermarks from aborting a comparison and does not report perfect NC for a nonzero watermark recovered as zero. Reliability and attack performance must be measured against the actual reference watermark for each experiment.
