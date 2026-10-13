import json
import os
import csv
import io
from pathlib import Path
import secrets
from uuid import uuid4

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, session, url_for
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
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)


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


@app.route("/preview/<path:filename>")
def preview(filename):
    safe_name = os.path.basename(filename)
    return send_from_directory(str(OUTPUT_FOLDER), safe_name, as_attachment=False)


@app.route("/api/results.csv")
def download_results_csv():
    results = session.get("latest_results", {}).get("attacks")
    if not results:
        return jsonify({"error": "No robustness experiment results are available."}), 404
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "attack", "parameters", "status", "psnr", "ssim", "nc", "ber",
        "extraction_time_ms", "error",
    ])
    for result in results:
        writer.writerow([
            result.get("attack"),
            json.dumps(result.get("attack_params", {}), sort_keys=True),
            result.get("status"),
            result.get("psnr"),
            result.get("ssim"),
            result.get("nc"),
            result.get("ber"),
            result.get("extraction_time_ms"),
            result.get("error", ""),
        ])
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=watermark-experiments.csv"},
    )


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
            subband=request.form.get("subband", "ALL"),
            alpha=float(request.form.get("alpha", 0.05)),
            key=request.form.get("key", ""),
            watermark_type=request.form.get("watermark_type", "grayscale"),
        )

        safe_stem = secure_filename(Path(cover_file.filename).stem) or "image"
        run_id = uuid4().hex
        safe_download_name = f"{safe_stem}_watermarked_{run_id}.png"
        output_name = OUTPUT_FOLDER / safe_download_name
        save_image_file(result["watermarked_image"], output_name)
        cover_preview = f"{safe_stem}_cover_{run_id}.png"
        save_image_file(cover, OUTPUT_FOLDER / cover_preview)
        result_payload = {
            "cover_name": cover_file.filename,
            "watermark_name": watermark_file.filename,
            "download_url": url_for("download", filename=safe_download_name),
            "watermarked_preview_url": url_for("preview", filename=safe_download_name),
            "cover_preview_url": url_for("preview", filename=cover_preview),
            "metrics": result["metrics"],
            "settings": result["settings"],
            "watermarked_image": output_name.name,
            "image_size": result["watermarked_image"].shape,
        }
        session["latest_results"] = result_payload
        return jsonify(result_payload), 200
    except Exception as exc:
        if isinstance(exc, ValueError):
            return jsonify({"error": str(exc)}), 400
        app.logger.exception("Unhandled error while embedding watermark.")
        return jsonify({"error": "The watermark could not be embedded due to a processing error."}), 500


@app.route("/api/extract", methods=["POST"])
def api_extract():
    try:
        watermarked_file = request.files.get("watermarked")
        original_file = request.files.get("original")
        original_watermark = request.files.get("reference_watermark")
        if watermarked_file is None or original_file is None or original_watermark is None:
            return jsonify({
                "error": "Watermarked image, original cover, and reference watermark are required."
            }), 400

        watermarked = read_image_file(watermarked_file)
        original = read_image_file(original_file)
        ref = read_image_file(original_watermark)

        result = extract_watermark(
            watermarked,
            original,
            wavelet=request.form.get("wavelet", "haar"),
            level=int(request.form.get("level", 1)),
            subband=request.form.get("subband", "ALL"),
            alpha=float(request.form.get("alpha", 0.05)),
            key=request.form.get("key", ""),
            original_watermark=ref,
            watermark_type=request.form.get("watermark_type", "grayscale"),
        )

        safe_stem = secure_filename(Path(watermarked_file.filename).stem) or "image"
        output_name = f"extracted_{safe_stem}_{uuid4().hex}.png"
        output_path = OUTPUT_FOLDER / output_name
        save_image_file(result["extracted_watermark"], output_path)
        reference_preview = f"reference_{uuid4().hex}.png"
        save_image_file(ref, OUTPUT_FOLDER / reference_preview)

        payload = {
            "download_url": url_for("download", filename=output_name),
            "extracted_preview_url": url_for("preview", filename=output_name),
            "reference_preview_url": url_for("preview", filename=reference_preview),
            "nc": result["nc"],
            "ber": result["ber"],
            "extraction_time_ms": result["extraction_time_ms"],
            "settings": result["settings"],
            "image_size": result["extracted_watermark"].shape,
        }
        session["latest_results"] = payload
        return jsonify(payload), 200
    except Exception as exc:
        if isinstance(exc, ValueError):
            return jsonify({"error": str(exc)}), 400
        app.logger.exception("Unhandled error while extracting watermark.")
        return jsonify({"error": "The watermark could not be extracted due to a processing error."}), 500


@app.route("/api/robustness", methods=["POST"])
def api_robustness():
    try:
        watermarked_file = request.files.get("watermarked")
        cover_file = request.files.get("cover")
        watermark_file = request.files.get("watermark")
        if watermarked_file is None or cover_file is None or watermark_file is None:
            return jsonify({
                "error": "Watermarked image, original cover, and reference watermark are required."
            }), 400

        watermarked = read_image_file(watermarked_file)
        cover = read_image_file(cover_file)
        watermark = read_image_file(watermark_file)
        attack_payload = request.form.get("attacks", "[]")
        attacks = json.loads(attack_payload) if attack_payload else []
        if not attacks:
            attacks = [
                {"name": "jpeg", "quality": 90},
                {"name": "jpeg", "quality": 70},
                {"name": "jpeg", "quality": 40},
                {"name": "gaussian_noise", "variance": 25, "seed": 0},
                {"name": "salt_pepper", "density": 0.01, "seed": 0},
                {"name": "gaussian_blur", "kernel_size": 5},
                {"name": "resize", "scale": 0.75},
                {"name": "brightness", "delta": 20},
                {"name": "contrast", "factor": 1.2},
                {"name": "crop", "crop_ratio": 0.8},
            ]

        results = run_robustness_experiment(
            watermarked,
            cover,
            watermark,
            attacks,
            wavelet=request.form.get("wavelet", "haar"),
            level=int(request.form.get("level", 1)),
            subband=request.form.get("subband", "ALL"),
            alpha=float(request.form.get("alpha", 0.05)),
            key=request.form.get("key", ""),
            watermark_type=request.form.get("watermark_type", "grayscale"),
        )
        for result in results:
            attacked_name = f"attack_{uuid4().hex}.png"
            save_image_file(result.pop("attacked_image"), OUTPUT_FOLDER / attacked_name)
            result["attacked_preview_url"] = url_for("preview", filename=attacked_name)
        payload = {"attacks": results}
        session["latest_results"] = payload
        return jsonify(payload), 200
    except Exception as exc:
        if isinstance(exc, ValueError):
            return jsonify({"error": str(exc)}), 400
        app.logger.exception("Unhandled error while running robustness experiments.")
        return jsonify({"error": "The robustness experiment failed due to a processing error."}), 500


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(debug=debug, host="127.0.0.1", port=5000)
