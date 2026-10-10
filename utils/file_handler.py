import os
from pathlib import Path

from config import OUTPUT_FOLDER, UPLOAD_FOLDER


def safe_output_name(filename):
    safe = os.path.basename(filename).strip()
    return safe if safe else "output.png"


def ensure_working_directories():
    for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
        Path(folder).mkdir(parents=True, exist_ok=True)
    return True
