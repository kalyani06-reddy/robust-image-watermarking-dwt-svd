import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff", "gif"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
APP_NAME = "Robust Image Watermarking Using DWT and SVD"

for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
    folder.mkdir(exist_ok=True)
