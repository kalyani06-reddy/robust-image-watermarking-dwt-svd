# Robust Image Watermarking Using DWT and SVD

A Python/Flask academic prototype for embedding and evaluating grayscale image watermarks. The application performs multilevel 2D DWT, block-based SVD embedding, non-blind extraction, reference-based metrics, and configurable image attack experiments.

**Algorithm details:** [docs/algorithm_explanation.md](docs/algorithm_explanation.md)
**Academic report and measured example:** [docs/academic_project_report.md](docs/academic_project_report.md)

## What is implemented

- Embeds each watermark sample in the largest singular value of a separate 2×2 block in a selected DWT subband or across all four subbands.
- Fits an oversized watermark to the available coefficient capacity automatically; extraction is upscaled to the reference dimensions, but detail removed during fitting cannot be recovered.
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
\(\lfloor r/2\rfloor\lfloor c/2\rfloor\) samples. **ALL** combines the capacity of LL, LH, HL, and HH (four times a single band for equal-size level-1 bands), and is the UI default. If a single-band selection cannot fit the watermark, the application automatically switches to **ALL**. If it is still too large, the watermark is downscaled with area interpolation to fit; extraction uses the same fit for comparison and enlarges the recovered image for display. The enlarged image cannot restore details lost during downscaling, so watermark capacity remains finite. A deeper DWT level usually makes each selected band smaller. Crops and geometric transformations can misalign the fixed block layout.

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

### Streamlit interface

The Streamlit app is the interactive image-watermarking workspace and reuses the same DWT–SVD algorithms as the Flask app:

```powershell
streamlit run streamlit_app.py
```

Open the local URL printed by Streamlit (normally <http://localhost:8501/>). The interface includes embedding, reference-based extraction, configurable attack experiments, measured strength tuning, result charts, and CSV export. Strength tuning compares 15 candidate strengths against selected attacks, excludes candidates below a configurable cover-PSNR floor (40 dB by default), and ranks the rest by attack coverage, mean NC, lower BER, then lower strength. The recommended image and its exact settings can be reused in the same browser session; uploaded images are limited to 16 MiB and 16 megapixels.

### Flask interface

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
5. **Tune strength (Streamlit):** provide the original cover and reference watermark, select representative attacks, and run the measured sweep. Candidates below the PSNR floor are excluded; the recommendation is optimized against the selected attacks, not every possible image transformation.
6. Open **Results** for the experiment table, NC/BER charts, and CSV export. The strength comparison can also be exported from the Robustness tab.

Uploads are limited to 16 MiB and decoded images to 16 megapixels. Accepted formats are PNG, JPEG, BMP, WEBP, TIFF, and GIF (the first frame is used for animated GIFs). Processing converts files to grayscale.

## Metrics and experiment interpretation

- **PSNR/SSIM:** compare the original cover with the actual saved, 8-bit watermarked output during embedding. For attack rows, compare the watermarked image with the attacked image.
- **NC:** conventional normalized correlation, \(\sum_i x_i y_i/\sqrt{\sum_i x_i^2\sum_i y_i^2}\), between aligned reference and recovered watermark samples in \([0,1]\).
- **BER:** fraction of corresponding reference/recovered samples whose values differ after thresholding at 0.5.
- **Execution time:** extraction wall-clock time in milliseconds; it varies with hardware and load.

Metrics reject mismatched dimensions and invalid ranges; arrays are never silently truncated. For the edge case of a black/zero watermark, NC is defined as 1 when both reference and extraction are all zero, and 0 when only one is zero. BER is still computed from the thresholded samples. An extraction failure is recorded with null NC/BER, not fabricated scores.

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

Tests cover multilevel/odd-sized DWT reconstruction, automatic capacity fitting, clean image recovery, reference-required extraction, metric input validation, attack failures, and Flask behavior. The recovery test asserts non-perfect NC and nonzero BER for its deterministic lossy case, and the no-reference test requires an error.

## Security and limitations

- Non-blind extraction needs the exact original cover and reference watermark.
- One watermark sample consumes one 2×2 block; the method has limited capacity.
- Modifying the selected subband's largest singular value can introduce visible distortion as strength rises; 8-bit output quantization also limits recovery.
- The simple fixed block grid has no synchronization or error-correction mechanism. Crop/resize and geometric changes may destroy alignment.
- A deterministic NumPy key permutation is not cryptographic protection.
- The Flask development server and local output folders are for local academic use; use a production WSGI server and deployment security review before deployment.

Runtime uploads/outputs, the Python virtual environment, and cache files are excluded from Git by [.gitignore](.gitignore).
