import csv
import json
from io import BytesIO, StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

from algorithms.robustness import run_robustness_experiment
from algorithms.strength_tuning import tune_watermark_strength
from algorithms.watermark_embedding import embed_watermark
from algorithms.watermark_extraction import extract_watermark
from config import ALLOWED_EXTENSIONS, APP_NAME, MAX_CONTENT_LENGTH

MAX_IMAGE_PIXELS = 16_000_000
EXPECTED_FORMATS = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "bmp": "BMP",
    "webp": "WEBP",
    "tif": "TIFF",
    "tiff": "TIFF",
    "gif": "GIF",
}


def read_uploaded_image(upload):
    if upload is None:
        raise ValueError("Please select an image.")

    extension = Path(upload.name).suffix.lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported image format.")
    if upload.size > MAX_CONTENT_LENGTH:
        raise ValueError("Image file exceeds the 16 MiB upload limit.")

    try:
        with Image.open(BytesIO(upload.getvalue())) as image:
            if image.format != EXPECTED_FORMATS[extension]:
                raise ValueError("Image contents do not match the file extension.")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions exceed the 16-megapixel processing limit.")
            image.seek(0)
            grayscale = ImageOps.exif_transpose(image).convert("L")
            grayscale.load()
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("The uploaded file is not a valid supported image.") from exc
    return np.asarray(grayscale, dtype=np.uint8)


def png_bytes(image):
    buffer = BytesIO()
    Image.fromarray(np.asarray(image, dtype=np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def current_settings():
    return {
        "wavelet": st.session_state.wavelet,
        "level": st.session_state.level,
        "subband": st.session_state.subband,
        "alpha": st.session_state.alpha,
        "key": st.session_state.secret_key,
        "watermark_type": st.session_state.watermark_type,
    }


def settings_for_upload(upload):
    if upload is None and "embedded_settings" in st.session_state:
        return st.session_state["embedded_settings"]
    return current_settings()


def image_input(label, key, required=False):
    uploaded = st.file_uploader(
        label,
        type=sorted(ALLOWED_EXTENSIONS),
        accept_multiple_files=False,
        key=key,
        help="PNG, JPEG, BMP, WEBP, TIFF, or GIF. Animated GIFs use their first frame.",
    )
    if required and uploaded is None:
        st.caption("Required for this operation.")
    return uploaded


def resolve_image(upload, session_key, label):
    if upload is not None:
        return read_uploaded_image(upload)
    image = st.session_state.get(session_key)
    if image is None:
        raise ValueError(f"Upload {label.lower()} or complete the embedding step first.")
    return image


def display_metrics(metrics):
    columns = st.columns(len(metrics))
    for column, (label, value) in zip(columns, metrics.items()):
        column.metric(label, value)


def display_comparison(left, right, left_label, right_label):
    columns = st.columns(2)
    columns[0].image(left, caption=left_label, use_container_width=True)
    columns[1].image(right, caption=right_label, use_container_width=True)


def get_attack_specs(selected):
    specs = []
    for attack in selected:
        if attack == "JPEG compression":
            values = st.text_input("JPEG qualities (comma-separated)", "90,70,40")
            try:
                qualities = [int(value.strip()) for value in values.split(",") if value.strip()]
            except ValueError as exc:
                raise ValueError("JPEG qualities must be comma-separated whole numbers.") from exc
            specs.extend({"name": "jpeg", "quality": quality} for quality in qualities)
        elif attack == "Gaussian noise":
            specs.append({"name": "gaussian_noise", "variance": st.number_input(
                "Gaussian noise variance", min_value=0.0, max_value=10000.0, value=25.0
            )})
        elif attack == "Salt-and-pepper noise":
            specs.append({"name": "salt_pepper", "density": st.number_input(
                "Salt-and-pepper density", min_value=0.0, max_value=1.0, value=0.01, step=0.01
            )})
        elif attack == "Gaussian blur":
            specs.append({"name": "gaussian_blur", "kernel_size": st.number_input(
                "Blur kernel size", min_value=1, max_value=99, value=5, step=2
            )})
        elif attack == "Resize":
            specs.append({"name": "resize", "scale": st.number_input(
                "Resize scale", min_value=0.01, max_value=4.0, value=0.75, step=0.05
            )})
        elif attack == "Brightness":
            specs.append({"name": "brightness", "delta": st.number_input(
                "Brightness delta", min_value=-255, max_value=255, value=20
            )})
        elif attack == "Contrast":
            specs.append({"name": "contrast", "factor": st.number_input(
                "Contrast factor", min_value=0.0, max_value=4.0, value=1.2, step=0.1
            )})
        elif attack == "Center crop":
            specs.append({"name": "crop", "crop_ratio": st.number_input(
                "Center crop ratio", min_value=0.01, max_value=1.0, value=0.8, step=0.05
            )})
    return specs


st.set_page_config(page_title=APP_NAME, page_icon="◈", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #151c24; color: #dce4e9; }
    [data-testid="stHeader"] { background: rgba(21, 28, 36, 0.9); }
    [data-testid="stSidebar"] { background: #19232d; border-right: 1px solid #34414e; }
    [data-testid="stMetric"] { background: #202a35; border: 1px solid #34414e; padding: 1rem; border-radius: 12px; }
    div[data-baseweb="tab-list"] { gap: .4rem; }
    button[data-baseweb="tab"] { color: #aebbc4; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #b6d0c4; border-bottom-color: #86a89b; }
    .stButton > button, .stDownloadButton > button { border-radius: 9px; }
    .home-hero {
        padding: 2.5rem;
        border: 1px solid #405164;
        border-radius: 18px;
        background: linear-gradient(120deg, #202d39 0%, #263a42 100%);
    }
    .home-eyebrow {
        color: #b6d0c4;
        font-size: .8rem;
        font-weight: 700;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .home-card {
        min-height: 150px;
        padding: 1.25rem;
        border: 1px solid #34414e;
        border-radius: 14px;
        background: #202a35;
    }
    .home-card h3 { color: #b6d0c4; font-size: 1.05rem; }
    .home-card p { color: #c2cdd4; margin-bottom: 0; }
    .home-workflow {
        padding: 1.25rem;
        border: 1px solid #34414e;
        border-radius: 14px;
        background: #19232d;
        color: #dce4e9;
        text-align: center;
        line-height: 2.2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("◈  Robust Image Watermarking")
st.caption("A DWT–SVD workspace for embedding, reference-based recovery, and measured robustness experiments.")

with st.sidebar:
    st.header("Embedding settings")
    st.caption("Use the same settings when extracting or testing an embedded watermark.")
    st.selectbox("Wavelet", ["haar", "db2", "sym2"], key="wavelet")
    st.select_slider("Decomposition level", options=[1, 2, 3], value=1, key="level")
    st.selectbox(
        "Subband",
        ["ALL", "LL", "LH", "HL", "HH"],
        format_func=lambda value: "All subbands (maximum capacity)" if value == "ALL" else value,
        key="subband",
    )
    st.slider("Watermark strength", 0.01, 0.30, 0.05, 0.01, key="alpha")
    st.selectbox("Watermark type", ["grayscale", "binary"], key="watermark_type")
    st.text_input("Optional secret key", type="password", key="secret_key")

home_tab, embed_tab, extract_tab, robustness_tab, results_tab = st.tabs(
    ["Home", "Embed", "Extract", "Robustness", "Results"]
)

with home_tab:
    st.markdown(
        """
        <section class="home-hero">
            <p class="home-eyebrow">Academic image security project</p>
            <h1>Robust Image Watermarking Using DWT and SVD</h1>
            <p>Secure digital image watermarking through frequency-domain transformation
            and singular-value decomposition.</p>
            <p><strong>Start here:</strong> choose the <em>Embed</em> tab above to add a
            watermark, or open <em>Robustness</em> to test an existing watermarked image.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Project features")
    feature_columns = st.columns(4)
    features = [
        ("Embed", "Insert a watermark into a cover image using DWT and SVD."),
        ("Extract", "Recover and compare a watermark using the original references."),
        ("Attack testing", "Benchmark JPEG, noise, blur, and geometric distortions."),
        ("Metrics", "Measure PSNR, SSIM, NC, BER, and execution time."),
    ]
    for column, (title, description) in zip(feature_columns, features):
        with column:
            st.markdown(
                f'<div class="home-card"><h3>{title}</h3><p>{description}</p></div>',
                unsafe_allow_html=True,
            )

    st.subheader("Embedding workflow")
    st.markdown(
        """
        <div class="home-workflow">
            Input image &nbsp; → &nbsp; DWT &nbsp; → &nbsp; SVD &nbsp; → &nbsp;
            Watermark embedding &nbsp; → &nbsp; Inverse DWT &nbsp; → &nbsp;
            Watermarked image
        </div>
        """,
        unsafe_allow_html=True,
    )

with embed_tab:
    st.subheader("Embed a watermark")
    st.write("Choose a cover image and reference watermark. The original files remain unchanged.")
    with st.form("embed_form"):
        cover_upload = image_input("Cover image", "embed_cover", required=True)
        watermark_upload = image_input("Watermark image", "embed_watermark", required=True)
        embed_submit = st.form_submit_button("Embed watermark", type="primary")

    if embed_submit:
        try:
            cover = read_uploaded_image(cover_upload)
            watermark = read_uploaded_image(watermark_upload)
            result = embed_watermark(cover, watermark, **current_settings())
            st.session_state["cover_image"] = cover
            st.session_state["reference_watermark"] = watermark
            st.session_state["watermarked_image"] = result["watermarked_image"]
            st.session_state["embedded_settings"] = current_settings()
            st.session_state["embed_result"] = result
        except ValueError as exc:
            st.error(str(exc))
        except np.linalg.LinAlgError:
            st.error("Embedding failed because the image decomposition was not numerically stable.")

    if "embed_result" in st.session_state:
        result = st.session_state["embed_result"]
        settings = result["settings"]
        display_metrics({
            "Cover PSNR": f'{result["metrics"]["psnr"]:.2f} dB',
            "Cover SSIM": f'{result["metrics"]["ssim"]:.5f}',
            "Embedding time": f'{result["metrics"]["embedding_time_ms"]:.2f} ms',
            "Payload capacity": f'{settings["watermark_capacity"]:,} samples',
        })
        display_comparison(
            st.session_state["cover_image"],
            result["watermarked_image"],
            "Original cover",
            "Watermarked cover",
        )
        if settings["watermark_resized"]:
            st.warning(
                f'Watermark reduced from {settings["source_watermark_shape"]} to '
                f'{settings["embedded_watermark_shape"]} to fit. Removed fine details cannot be restored.'
            )
        st.download_button(
            "Download watermarked PNG",
            data=png_bytes(result["watermarked_image"]),
            file_name="watermarked.png",
            mime="image/png",
        )

with extract_tab:
    st.subheader("Extract and compare")
    st.write("Non-blind extraction needs the exact original cover and original reference watermark.")
    if "watermarked_image" in st.session_state:
        st.info("Leave the watermarked upload empty to reuse the last embedded image and its exact settings.")
    with st.form("extract_form"):
        watermarked_upload = image_input("Watermarked image", "extract_watermarked")
        original_upload = image_input("Original cover image", "extract_cover")
        reference_upload = image_input("Reference watermark", "extract_reference")
        extract_submit = st.form_submit_button("Extract watermark", type="primary")

    if extract_submit:
        try:
            watermarked = resolve_image(watermarked_upload, "watermarked_image", "watermarked image")
            original = resolve_image(original_upload, "cover_image", "original cover")
            reference = resolve_image(reference_upload, "reference_watermark", "reference watermark")
            result = extract_watermark(
                watermarked,
                original,
                original_watermark=reference,
                **settings_for_upload(watermarked_upload),
            )
            st.session_state["extract_result"] = result
            st.session_state["extract_reference_image"] = reference
        except ValueError as exc:
            st.error(str(exc))
        except np.linalg.LinAlgError:
            st.error("Extraction failed because the image decomposition was not numerically stable.")

    if "extract_result" in st.session_state:
        result = st.session_state["extract_result"]
        display_metrics({
            "Normalized correlation": f'{result["nc"]:.5f}',
            "Bit error rate": f'{result["ber"]:.5f}',
            "Extraction time": f'{result["extraction_time_ms"]:.2f} ms',
        })
        display_comparison(
            st.session_state["extract_reference_image"],
            result["extracted_watermark"],
            "Reference watermark",
            "Extracted watermark",
        )
        st.download_button(
            "Download extracted PNG",
            data=png_bytes(result["extracted_watermark"]),
            file_name="extracted_watermark.png",
            mime="image/png",
        )

with robustness_tab:
    st.subheader("Run robustness experiments")
    st.write("Each selected attack is applied to the watermarked image and then passed through actual extraction.")
    if "watermarked_image" in st.session_state:
        st.info("Leave the watermarked upload empty to reuse the last embedded image and its exact settings.")
    attack_choices = st.multiselect(
        "Select attacks",
        [
            "JPEG compression",
            "Gaussian noise",
            "Salt-and-pepper noise",
            "Gaussian blur",
            "Resize",
            "Brightness",
            "Contrast",
            "Center crop",
        ],
        default=["JPEG compression", "Gaussian noise", "Gaussian blur"],
    )
    with st.form("robustness_form"):
        watermarked_upload = image_input("Watermarked image", "robust_watermarked")
        original_upload = image_input("Original cover image", "robust_cover")
        reference_upload = image_input("Reference watermark", "robust_reference")
        attack_specs = get_attack_specs(attack_choices)
        psnr_floor = st.number_input(
            "Minimum cover PSNR for tuning (dB)",
            min_value=0.0,
            max_value=100.0,
            value=40.0,
            step=1.0,
            help="Candidates below this imperceptibility floor are excluded from strength tuning.",
        )
        tune_submit = st.form_submit_button("Tune strength")
        robustness_submit = st.form_submit_button("Run experiments", type="primary")

    if tune_submit:
        try:
            original = resolve_image(original_upload, "cover_image", "original cover image")
            reference = resolve_image(reference_upload, "reference_watermark", "reference watermark")
            tuning = tune_watermark_strength(
                original,
                reference,
                attack_specs,
                psnr_floor=psnr_floor,
                **current_settings(),
            )
            st.session_state["strength_tuning"] = tuning
            if tuning["recommended_embedding"] is not None:
                embedding = tuning["recommended_embedding"]
                settings = dict(current_settings())
                settings["alpha"] = tuning["recommended_strength"]
                st.session_state["cover_image"] = original
                st.session_state["reference_watermark"] = reference
                st.session_state["watermarked_image"] = embedding["watermarked_image"]
                st.session_state["embedded_settings"] = settings
                st.session_state["embed_result"] = embedding
        except ValueError as exc:
            st.error(str(exc))
        except np.linalg.LinAlgError:
            st.error("Strength tuning failed because the image decomposition was not numerically stable.")

    elif robustness_submit:
        try:
            watermarked = resolve_image(watermarked_upload, "watermarked_image", "watermarked image")
            original = resolve_image(original_upload, "cover_image", "original cover")
            reference = resolve_image(reference_upload, "reference_watermark", "reference watermark")
            results = run_robustness_experiment(
                watermarked,
                original,
                reference,
                attack_specs,
                **settings_for_upload(watermarked_upload),
            )
            rows = []
            for item in results:
                rows.append({
                    key: item.get(key)
                    for key in (
                        "attack", "attack_params", "status", "psnr", "ssim", "nc",
                        "ber", "extraction_time_ms", "error",
                    )
                })
            st.session_state["experiment_rows"] = rows
            st.session_state["experiment_images"] = [
                (item["attack"], item["attack_params"], item["attacked_image"])
                for item in results
            ]
        except ValueError as exc:
            st.error(str(exc))
        except np.linalg.LinAlgError:
            st.error("The experiment failed because the image decomposition was not numerically stable.")

    if "strength_tuning" in st.session_state:
        tuning = st.session_state["strength_tuning"]
        st.subheader("Measured strength comparison")
        tuning_rows = tuning["trials"]
        st.dataframe(
            [
                {
                    "Strength": row["strength"],
                    "Cover PSNR (dB)": row["cover_psnr"],
                    "Cover SSIM": row["cover_ssim"],
                    "Mean attack NC": row["mean_nc"],
                    "Mean attack BER": row["mean_ber"],
                    "Measured attacks": f'{row["measured_attacks"]} / {row["total_attacks"]}',
                    "Status": row["status"].replace("_", " ").title(),
                }
                for row in tuning_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
        measurable_trials = [row for row in tuning_rows if row["mean_nc"] is not None]
        if measurable_trials:
            chart_data = pd.DataFrame(
                [
                    {
                        "Strength": row["strength"],
                        "Mean attack NC": row["mean_nc"],
                        "Cover PSNR (dB)": row["cover_psnr"],
                    }
                    for row in measurable_trials
                ]
            ).set_index("Strength")
            chart_columns = st.columns(2)
            chart_columns[0].caption("Mean normalized correlation under selected attacks")
            chart_columns[0].line_chart(chart_data[["Mean attack NC"]])
            chart_columns[1].caption("Cover imperceptibility")
            chart_columns[1].line_chart(chart_data[["Cover PSNR (dB)"]])

        csv_buffer = StringIO()
        tuning_fields = [
            "strength", "cover_psnr", "cover_ssim", "mean_nc", "mean_ber",
            "measured_attacks", "total_attacks", "status",
        ]
        writer = csv.DictWriter(csv_buffer, fieldnames=tuning_fields)
        writer.writeheader()
        writer.writerows(tuning_rows)
        st.download_button(
            "Export strength comparison as CSV",
            data=csv_buffer.getvalue(),
            file_name="watermark-strength-comparison.csv",
            mime="text/csv",
        )

        if tuning["recommended_embedding"] is None:
            st.warning(
                "No candidate above the PSNR floor produced a measurable extraction for the selected attacks."
            )
        else:
            best = tuning["recommended_embedding"]
            st.success(
                f'Recommended strength: {tuning["recommended_strength"]:.4f}. '
                "The tuner ranks candidates by measured attack coverage, mean NC, "
                "lower BER, then lower strength."
            )
            display_metrics({
                "Recommended cover PSNR": f'{best["metrics"]["psnr"]:.2f} dB',
                "Recommended cover SSIM": f'{best["metrics"]["ssim"]:.5f}',
                "Embedding time": f'{best["metrics"]["embedding_time_ms"]:.2f} ms',
            })
            st.image(best["watermarked_image"], caption="Recommended tuned watermarked image")
            st.download_button(
                "Download tuned watermarked PNG",
                data=png_bytes(best["watermarked_image"]),
                file_name="tuned-watermarked.png",
                mime="image/png",
            )
            st.caption(
                "The tuned image and its exact settings are saved in this browser session "
                "for the Extract and Robustness tabs."
            )

    if st.session_state.get("experiment_rows"):
        rows = st.session_state["experiment_rows"]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        for name, params, attacked in st.session_state.get("experiment_images", []):
            with st.expander(f"Attacked preview: {name} — {params}"):
                st.image(attacked, use_container_width=True)

with results_tab:
    st.subheader("Experiment results")
    rows = st.session_state.get("experiment_rows", [])
    if not rows:
        st.info("Run at least one robustness experiment to populate results.")
    else:
        measured = [
            row for row in rows
            if row["status"] == "measured"
            and row["nc"] is not None
            and row["ber"] is not None
        ]
        columns = st.columns(4)
        columns[0].metric("Total tests", len(rows))
        columns[1].metric("Metrics available", f"{len(measured)} / {len(rows)}")
        columns[2].metric(
            "Mean NC",
            f'{np.mean([row["nc"] for row in measured]):.4f}' if measured else "—",
        )
        columns[3].metric(
            "Mean BER",
            f'{np.mean([row["ber"] for row in measured]):.4f}' if measured else "—",
        )
        st.caption("Unavailable extractions have no NC or BER score; metrics are never fabricated.")
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if measured:
            chart_data = pd.DataFrame.from_dict(
                {
                    f'{row["attack"]} {row["attack_params"]}': {
                        "NC": row["nc"],
                        "BER": row["ber"],
                    }
                    for row in measured
                },
                orient="index",
            )
            st.bar_chart(chart_data)

        csv_buffer = StringIO()
        fieldnames = [
            "attack", "parameters", "status", "psnr", "ssim", "nc",
            "ber", "extraction_time_ms", "error",
        ]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "attack": row["attack"],
                "parameters": json.dumps(row["attack_params"], sort_keys=True),
                "status": row["status"],
                "psnr": row["psnr"],
                "ssim": row["ssim"],
                "nc": row["nc"],
                "ber": row["ber"],
                "extraction_time_ms": row["extraction_time_ms"],
                "error": row["error"],
            })
        st.download_button(
            "Export validated results as CSV",
            data=csv_buffer.getvalue(),
            file_name="watermark-experiments.csv",
            mime="text/csv",
        )
