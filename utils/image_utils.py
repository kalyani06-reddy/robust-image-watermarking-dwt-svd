import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from config import ALLOWED_EXTENSIONS


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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
    img = Image.open(file_storage)
    img = img.convert("L")
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
