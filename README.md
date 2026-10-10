# Robust Image Watermarking Using DWT and SVD

A Python/Flask research prototype for experimenting with grayscale image watermarking in the wavelet domain. The application uses a one-level 2D Discrete Wavelet Transform (DWT), modifies singular values of a selected subband, reconstructs the image, and provides an interface for embedding, non-blind extraction, and attack experiments.

**Academic report:** [docs/academic_project_report.md](docs/academic_project_report.md)  
**Algorithm note:** [docs/algorithm_explanation.md](docs/algorithm_explanation.md)

## What the application does

- Accepts grayscale cover and watermark images in PNG, JPG/JPEG, or BMP formats.
- Embeds a resized, flattened watermark vector into singular values of a selected DWT subband.
- Reconstructs and offers the watermarked image for download.
- Provides non-blind extraction, which requires the original cover and matching settings.
- Contains image attack functions for JPEG compression, Gaussian noise, salt-and-pepper noise, blur, resizing, brightness, contrast, and crop-and-resize.
- Calculates PSNR and SSIM for image quality, and has NC and BER utilities for watermark comparisons.

## Important implementation scope

This is a working academic prototype, not a production watermarking or security system. The current algorithm uses `pywt.dwt2` once; the UI's decomposition-level setting is not yet applied as a multi-level transform. The watermark is flattened and sampled to the singular-value vector length, so the method does not preserve the full spatial watermark resolution. Extraction returns a vector rather than restoring the original watermark geometry.

Extraction requires the original cover image. The extraction UI does not currently upload a reference watermark, so reported NC/BER from that path are not meaningful comparisons: without a reference, the implementation compares the recovered vector with itself and reports BER as zero. The robustness endpoint and dashboard also need further integration and validation before their output should be treated as measured experiment results. See the report's limitations section.

The optional key controls a deterministic permutation generated from a SHA-256-derived seed and NumPy's pseudorandom generator. It is not a cryptographically secure watermark encryption mechanism. Do not use a production or reused secret key with this prototype.

## Requirements

Python 3.11 or later is recommended. Dependencies are listed in [requirements.txt](requirements.txt). The workspace used for verification has Python 3.14.7.

## Install

From the project directory in Windows PowerShell:

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

## Run

```bash
python app.py
```

Open <http://127.0.0.1:5000/>. The Flask development server is for local development only. Do not expose it to an untrusted network.

## Basic workflow

1. On **Embed**, upload a cover image and a watermark image, then choose the wavelet, subband, and strength.
2. Download the watermarked PNG returned by the application.
3. On **Extract**, provide the watermarked image, the exact original cover image, and the same wavelet, subband, strength, and optional key.
4. On **Robustness**, provide the watermarked image and its original cover. Interpret its output cautiously until the robustness endpoint's image serialization and reference-watermark evaluation are corrected.

The current upload limit is 16 MiB. Image processing converts uploaded images to grayscale.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Home page |
| GET | `/embed` | Embedding form |
| POST | `/api/embed` | Embed and save a watermarked image |
| GET | `/extract` | Extraction form |
| POST | `/api/extract` | Non-blind extraction |
| GET | `/robustness` | Robustness form |
| POST | `/api/robustness` | Run selected attack experiments |
| GET | `/results` | Results page |
| GET | `/download/<filename>` | Download an output image |

## Metrics

- **PSNR:** logarithmic mean-squared error measure between cover and watermarked image, using an 8-bit peak value of 255.
- **SSIM:** structural similarity computed by scikit-image.
- **NC:** the utility implements mean-centered normalized correlation (Pearson-style correlation). Its value is only informative when comparing corresponding original and recovered watermark samples.
- **BER:** fraction of thresholded samples that differ. Inputs must be corresponding, normalized watermark samples; truncating mismatched arrays is not a valid spatial alignment strategy.
- **Execution time:** measured with a monotonic high-resolution performance counter and reported in milliseconds.

No benchmark table is included because representative experiments have not been collected and validated. The automated test suite currently passes, but its extraction test does not pass a reference watermark and therefore does not validate true recovery accuracy.

## Tests

```powershell
python -m pytest -q
```

Last verified in this workspace: **8 passed**. This verifies the present test assertions, not research-grade robustness or watermark recovery quality.

## Project layout

```text
app.py                      Flask routes and page rendering
config.py                   Upload/output configuration
algorithms/                 DWT, SVD, embedding, extraction, attacks
utils/                      Image handling and metrics
templates/                  Flask HTML pages
static/                     CSS and JavaScript
tests/                      Pytest checks
docs/                       Academic report and algorithm note
uploads/                    Runtime upload directory (ignored by Git)
outputs/                    Runtime output directory (ignored by Git)
```

## Security and deployment notes

The current app contains a hard-coded Flask session secret, runs with Flask debug mode enabled, and returns detailed exception messages from API handlers. These choices are unsuitable for public deployment. Before deployment, configure a random secret from an environment variable, disable debug mode, validate all numerical parameters, return generic client errors, add content-based image validation, and use a production WSGI server. The upload and output directories should be treated as local prototype storage.

## GitHub setup

The `.gitignore` excludes the virtual environment, Python caches, uploads, and generated outputs. To publish the source:

```bash
git init
git add .
git commit -m "Add DWT-SVD watermarking project"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```

Never commit credentials, secret keys, or private images.
