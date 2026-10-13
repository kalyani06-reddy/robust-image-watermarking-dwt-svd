import gradio as gr
import numpy as np
import pywt
import cv2
from PIL import Image


def calculate_psnr(original, reconstructed):
    original = original.astype(np.float64)
    reconstructed = reconstructed.astype(np.float64)

    mse = np.mean((original - reconstructed) ** 2)

    if mse == 0:
        return float("inf")

    return 10 * np.log10((255.0 ** 2) / mse)


def calculate_ssim(original, reconstructed):
    # Global SSIM approximation using NumPy only.
    x = original.astype(np.float64)
    y = reconstructed.astype(np.float64)

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    mean_x = np.mean(x)
    mean_y = np.mean(y)

    var_x = np.var(x)
    var_y = np.var(y)
    covariance = np.mean((x - mean_x) * (y - mean_y))

    numerator = (2 * mean_x * mean_y + c1) * (
        2 * covariance + c2
    )
    denominator = (mean_x ** 2 + mean_y ** 2 + c1) * (
        var_x + var_y + c2
    )

    return numerator / denominator


def analyze_image(image):
    if image is None:
        raise gr.Error("Please upload a cover image.")

    rgb = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    ll, (lh, hl, hh) = pywt.dwt2(
        gray.astype(np.float32), "haar"
    )

    reconstructed = pywt.idwt2((ll, (lh, hl, hh)), "haar")
    reconstructed = np.clip(
        reconstructed, 0, 255
    ).astype(np.uint8)

    reconstructed = reconstructed[:gray.shape[0], :gray.shape[1]]

    psnr = calculate_psnr(gray, reconstructed)
    ssim = calculate_ssim(gray, reconstructed)

    subbands = [
        Image.fromarray(np.clip(ll, 0, 255).astype(np.uint8)),
        Image.fromarray(np.clip(lh + 128, 0, 255).astype(np.uint8)),
        Image.fromarray(np.clip(hl + 128, 0, 255).astype(np.uint8)),
        Image.fromarray(np.clip(hh + 128, 0, 255).astype(np.uint8)),
    ]

    metrics = f"PSNR: {psnr:.2f} dB\nSSIM (global approximation): {ssim:.6f}"

    return Image.fromarray(reconstructed), subbands, metrics


with gr.Blocks(title="DWT-SVD Image Watermarking") as demo:
    gr.Markdown("# Robust Image Watermarking Using DWT and SVD")
    gr.Markdown("Explore DWT frequency subbands and reconstruction quality.")

    image_input = gr.Image(type="pil", label="Upload Cover Image")
    analyze_button = gr.Button("Analyze Image", variant="primary")

    reconstructed_output = gr.Image(label="Reconstructed Image")
    subband_output = gr.Gallery(label="DWT Subbands", columns=2)
    metrics_output = gr.Textbox(label="Image Quality Metrics")

    analyze_button.click(
        analyze_image,
        inputs=image_input,
        outputs=[reconstructed_output, subband_output, metrics_output],
    )


if __name__ == "__main__":
    demo.launch()