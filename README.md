# Robust Image Watermarking Using DWT and SVD

A Python/Flask academic prototype for embedding and evaluating grayscale image watermarks. The application performs multilevel 2D DWT, block-based SVD embedding, non-blind extraction, reference-based metrics, and configurable image attack experiments.

**Algorithm details:** [docs/algorithm_explanation.md](docs/algorithm_explanation.md)
**Academic report and measured example:** [docs/academic_project_report.md](docs/academic_project_report.md)

## What is implemented

- Embeds each watermark sample in the largest singular value of a separate 2×2 block in a selected DWT subband.
- Preserves the watermark's dimensions and rejects a watermark that exceeds available coefficient capacity instead of silently resizing it.
- Uses the chosen wavelet, decomposition level, subband, strength, watermark type, and optional deterministic key consistently during embedding and extraction.
- Performs **non-blind extraction** using the exact original cover and reference watermark. The reference is required both to restore the original watermark dimensions and to calculate meaningful NC/BER.
- Reports cover/watermarked PSNR and SSIM; reports NC and BER only from reference-versus-extracted watermark samples.
- Runs JPEG quality, Gaussian noise, salt-and-pepper noise, blur, resize, brightness, contrast, and crop experiments by actually attacking and extracting each image.
- Saves attack outputs, displays experiment metrics/charts, and exports the measured rows to CSV.

This remains an educational prototype, not a production ownership, authentication, or security system. A metric being available does not establish that a watermark survived an attack; inspect NC and BER alongside the recovered image and test results.

## Algorithm summary

For every watermark pixel \(w_i\), normalized to \([0,1]\), the selected wavelet band is divided into non-overlapping 2×2 blocks. For block \(B_i=U_i\Sigma_iV_i^T\), embedding changes only its largest singular value:

$$
\sigma'_{i,1}=\sigma_{i,1}+192\alpha w_{\pi(i)}, \qquad
B'_i=U_i\operatorname{diag}(\sigma'_{i,1},\sigma_{i,2})V_i^T.
$$

The inverse DWT reconstructs the watermarked image. Extraction compares the largest singular values of the watermarked and original-cover blocks:

$$
\hat{w}_{\pi(i)}=\operatorname{clip}\left(
\frac{\sigma^{(w)}_{i,1}-\sigma^{(c)}_{i,1}}{192\alpha},0,1
\right).
$$

The required reference watermark supplies the expected dimensions. Its samples are not substituted for recovered samples. The optional key supplies a reproducible permutation only; it is not encryption.

The capacity for an \(r\times c\) selected band is
\(\lfloor r/2\rfloor\lfloor c/2\rfloor\) samples. A deeper DWT level usually makes the selected band smaller. Crops and geometric transformations can misalign the fixed block layout.

## Requirements and installation

Python 3.11 or later is recommended. The packages are listed in [requirements.txt](requirements.txt).

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run locally

```powershell
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-value"
python app.py
```

The app binds to `127.0.0.1:5000` and has debug mode off by default. To explicitly enable the development debugger locally, set `FLASK_DEBUG=1`; do not do so on a public server. If `FLASK_SECRET_KEY` is unset, a random process-local key is generated and sessions will not survive an app restart.

Open <http://127.0.0.1:5000/>.

## Basic workflow

1. **Embed:** upload the cover and watermark. Record the settings (wavelet, level, subband, strength, watermark type, and optional key); use the same settings for extraction.
2. Download the watermarked PNG. The original uploaded image is not overwritten.
3. **Extract:** upload the watermarked image, exact original cover, and exact reference watermark. Extraction without those references is rejected.
4. **Robustness:** provide those same three images and matching settings. Select attacks and strengths; JPEG accepts a comma-separated list of quality values. Each row reports extraction metrics only when a reference-based comparison can be computed.
5. Open **Results** for the experiment table, NC/BER charts, and CSV export.

Uploads are limited to 16 MiB, decoded images to 16 megapixels, and accepted formats are PNG, JPEG, and BMP. Processing converts files to grayscale.

## Metrics and experiment interpretation

- **PSNR/SSIM:** compare the original cover with the actual saved, 8-bit watermarked output during embedding. For attack rows, compare the watermarked image with the attacked image.
- **NC:** conventional normalized correlation, \(\sum_i x_i y_i/\sqrt{\sum_i x_i^2\sum_i y_i^2}\), between aligned reference and recovered watermark samples in \([0,1]\).
- **BER:** fraction of corresponding reference/recovered samples whose values differ after thresholding at 0.5.
- **Execution time:** extraction wall-clock time in milliseconds; it varies with hardware and load.

Metrics reject mismatched dimensions, invalid ranges, and undefined zero-vector comparisons; arrays are never silently truncated. An extraction failure is recorded with null NC/BER, not fabricated scores.

### One deterministic synthetic example

The current implementation was run on one generated 128×128 grayscale cover (NumPy seed 20261011) and a 32×32 binary checkerboard watermark, with Haar, level 1, LL, strength 0.05, and key `demo-key`. Clean extraction measured NC **0.9963**, BER **0.0000**, cover PSNR **45.29 dB**, and SSIM **0.99988**. The attack rows and limitations are in the academic report. These are one synthetic demonstration, not a general performance claim or an independently validated benchmark.

## Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Home |
| GET | `/embed`, `/extract`, `/robustness`, `/results` | Application pages |
| POST | `/api/embed` | Embed and return metrics and preview/download links |
| POST | `/api/extract` | Reference-based non-blind extraction |
| POST | `/api/robustness` | Run selected attack experiments |
| GET | `/api/results.csv` | Download the latest experiment results |
| GET | `/preview/<filename>` | Display a generated output image |
| GET | `/download/<filename>` | Download a generated output image |

## Tests

```powershell
python -m pytest -q
```

Tests cover multilevel/odd-sized DWT reconstruction, capacity rejection, clean image recovery, reference-required extraction, metric input validation, attack failures, and Flask behavior. The recovery test asserts non-perfect NC and nonzero BER for its deterministic lossy case, and the no-reference test requires an error.

## Security and limitations

- Non-blind extraction needs the exact original cover and reference watermark.
- One watermark sample consumes one 2×2 block; the method has limited capacity.
- Modifying the selected subband's largest singular value can introduce visible distortion as strength rises; 8-bit output quantization also limits recovery.
- The simple fixed block grid has no synchronization or error-correction mechanism. Crop/resize and geometric changes may destroy alignment.
- A deterministic NumPy key permutation is not cryptographic protection.
- The Flask development server and local output folders are for local academic use; use a production WSGI server and deployment security review before deployment.

Runtime uploads/outputs, the Python virtual environment, and cache files are excluded from Git by [.gitignore](.gitignore).
