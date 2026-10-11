import os
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from config import ALLOWED_EXTENSIONS


def allowed_file(filename):
    return (
        isinstance(filename, str)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def ensure_uint8(image_array):
    arr = np.asarray(image_array, dtype=np.float64)
    arr = np.clip(arr, 0, 255)
    return arr.astype(np.uint8)


def read_image_file(file_storage):
    if file_storage is None:
        raise ValueError("No file was uploaded.")
    filename = file_storage.filename
    if not allowed_file(filename):
        raise ValueError("Unsupported image format.")
    try:
        content = file_storage.read()
        img = Image.open(BytesIO(content))
        if img.width * img.height > 16_000_000:
            raise ValueError("Image dimensions exceed the 16-megapixel processing limit.")
        expected_format = Path(filename).suffix.lower().lstrip(".")
        accepted_formats = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "bmp": "BMP"}
        if img.format != accepted_formats[expected_format]:
            raise ValueError("Image contents do not match the file extension.")
        img.load()
        img = img.convert("L")
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Uploaded file is not a valid supported image.") from exc
    return np.asarray(img, dtype=np.uint8)


def load_image_array(image_path):
    image = Image.open(image_path)
    return np.asarray(image.convert("L"), dtype=np.uint8)


def save_image_file(image_array, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(image_array, dtype=np.uint8)).save(output)
    return str(output)


def are_valid_image_files(files):
    for file in files:
        if file is None:
            return False
        if not allowed_file(file.filename):
            return False
    return True
