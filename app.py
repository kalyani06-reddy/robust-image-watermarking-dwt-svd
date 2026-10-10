import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from algorithms.watermark_embedding import embed_watermark
from algorithms.watermark_extraction import extract_watermark
from algorithms.robustness import run_robustness_experiment
from config import APP_NAME, BASE_DIR, MAX_CONTENT_LENGTH, OUTPUT_FOLDER, UPLOAD_FOLDER
from utils.image_utils import read_image_file, save_image_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["OUTPUT_FOLDER"] = str(OUTPUT_FOLDER)
app.config["SECRET_KEY"] = "robust-watermark-demo-key"


@app.route("/")
def home():
    return render_template("index.html", app_name=APP_NAME)


@app.route("/embed")
def embed_page():
    return render_template("embed.html", app_name=APP_NAME)


@app.route("/extract")
def extract_page():
    return render_template("extract.html", app_name=APP_NAME)


@app.route("/robustness")
def robustness_page():
    return render_template("robustness.html", app_name=APP_NAME)


@app.route("/results")
def results_page():
    data = session.get("latest_results", {})
    return render_template("results.html", app_name=APP_NAME, result_data=data)


@app.route("/download/<path:filename>")
def download(filename):
    safe_name = os.path.basename(filename)
    return send_from_directory(str(OUTPUT_FOLDER), safe_name, as_attachment=True)


@app.route("/api/embed", methods=["POST"])
def api_embed():
    try:
        cover_file = request.files.get("cover")
        watermark_file = request.files.get("watermark")
        if cover_file is None or watermark_file is None:
            return jsonify({"error": "Cover image and watermark image are required."}), 400

        cover = read_image_file(cover_file)
        watermark = read_image_file(watermark_file)
        result = embed_watermark(
            cover,
            watermark,
            wavelet=request.form.get("wavelet", "haar"),
            level=int(request.form.get("level", 1)),
            subband=request.form.get("subband", "LL"),
            alpha=float(request.form.get("alpha", 0.05)),
            key=request.form.get("key", ""),
        )

        safe_download_name = secure_filename(f"{Path(cover_file.filename).stem}_watermarked.png")
        output_name = OUTPUT_FOLDER / safe_download_name
        save_image_file(result["watermarked_image"], output_name)
        result_payload = {
            "cover_name": cover_file.filename,
            "watermark_name": watermark_file.filename,
            "download_url": url_for("download", filename=safe_download_name),
            "metrics": result["metrics"],
            "settings": result["settings"],
            "watermarked_image": output_name.name,
            "image_size": result["watermarked_image"].shape,
        }
        session["latest_results"] = result_payload
        return jsonify(result_payload), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/extract", methods=["POST"])
def api_extract():
    try:
        watermarked_file = request.files.get("watermarked")
        original_file = request.files.get("original")
        if watermarked_file is None:
            return jsonify({"error": "Watermarked image is required."}), 400

        watermarked = read_image_file(watermarked_file)
        original = read_image_file(original_file) if original_file else None
        original_watermark = request.files.get("reference_watermark")
        ref = read_image_file(original_watermark) if original_watermark else None

        result = extract_watermark(
            watermarked,
            original,
            wavelet=request.form.get("wavelet", "haar"),
            level=int(request.form.get("level", 1)),
            subband=request.form.get("subband", "LL"),
            alpha=float(request.form.get("alpha", 0.05)),
            key=request.form.get("key", ""),
            original_watermark=ref,
        )

        output_name = secure_filename(f"extracted_{Path(watermarked_file.filename).stem}.png")
        output_path = OUTPUT_FOLDER / output_name
        save_image_file(result["extracted_watermark"], output_path)

        payload = {
            "download_url": url_for("download", filename=output_name),
            "nc": result["nc"],
            "ber": result["ber"],
            "extraction_time_ms": result["extraction_time_ms"],
            "settings": result["settings"],
            "image_size": result["extracted_watermark"].shape,
        }
        session["latest_results"] = payload
        return jsonify(payload), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/robustness", methods=["POST"])
def api_robustness():
    try:
        watermarked_file = request.files.get("watermarked")
        cover_file = request.files.get("cover")
        watermark_file = request.files.get("watermark")
        if watermarked_file is None or cover_file is None:
            return jsonify({"error": "Watermarked image and original cover are required."}), 400

        watermarked = read_image_file(watermarked_file)
        cover = read_image_file(cover_file)
        watermark = read_image_file(watermark_file) if watermark_file else None
        attack_payload = request.form.get("attacks", "[]")
        attacks = json.loads(attack_payload) if attack_payload else []
        if not attacks:
            attacks = [
                {"name": "jpeg", "quality": 80},
                {"name": "gaussian_noise", "variance": 0.01},
                {"name": "salt_pepper", "density": 0.01},
                {"name": "gaussian_blur", "kernel_size": 5},
                {"name": "brightness", "delta": 20},
            ]

        results = run_robustness_experiment(
            watermarked,
            cover,
            watermark,
            attacks,
            wavelet=request.form.get("wavelet", "haar"),
            level=int(request.form.get("level", 1)),
            subband=request.form.get("subband", "LL"),
            alpha=float(request.form.get("alpha", 0.05)),
            key=request.form.get("key", ""),
        )
        return jsonify({"attacks": results}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
