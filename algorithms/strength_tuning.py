import numpy as np

from algorithms.robustness import run_robustness_experiment
from algorithms.watermark_embedding import embed_watermark

DEFAULT_STRENGTHS = tuple(
    round(float(value), 4) for value in np.linspace(0.01, 0.30, 15)
)


def tune_watermark_strength(
    cover_image,
    watermark_image,
    attack_specs,
    *,
    psnr_floor=40.0,
    strengths=DEFAULT_STRENGTHS,
    **settings,
):
    if not attack_specs:
        raise ValueError("At least one attack specification is required for strength tuning.")

    psnr_floor = float(psnr_floor)
    if not np.isfinite(psnr_floor) or psnr_floor < 0:
        raise ValueError("Minimum cover PSNR must be a finite non-negative number.")

    try:
        candidate_strengths = [float(value) for value in strengths]
    except (TypeError, ValueError) as exc:
        raise ValueError("Strength candidates must be finite numbers.") from exc
    if not candidate_strengths or any(
        not np.isfinite(value) or value <= 0 or value > 0.3
        for value in candidate_strengths
    ):
        raise ValueError("Strength candidates must be greater than 0 and at most 0.3.")
    if len(set(candidate_strengths)) != len(candidate_strengths):
        raise ValueError("Strength candidates must be unique.")

    trials = []
    eligible = []
    embedding_settings = {
        key: value for key, value in settings.items() if key != "alpha"
    }
    for strength in candidate_strengths:
        embedding = embed_watermark(
            cover_image,
            watermark_image,
            alpha=strength,
            **embedding_settings,
        )
        metrics = embedding["metrics"]
        trial = {
            "strength": strength,
            "cover_psnr": metrics["psnr"],
            "cover_ssim": metrics["ssim"],
            "measured_attacks": 0,
            "total_attacks": len(attack_specs),
            "mean_nc": None,
            "mean_ber": None,
            "status": "below_psnr" if metrics["psnr"] < psnr_floor else "pending",
        }
        trials.append(trial)

        if metrics["psnr"] < psnr_floor:
            continue

        attack_results = run_robustness_experiment(
            embedding["watermarked_image"],
            cover_image,
            watermark_image,
            attack_specs,
            alpha=strength,
            **{
                key: value
                for key, value in embedding_settings.items()
                if key in ("wavelet", "level", "subband", "key", "watermark_type")
            },
        )
        measured = [
            result for result in attack_results
            if result["status"] == "measured"
            and result["nc"] is not None
            and result["ber"] is not None
        ]
        trial.update(
            measured_attacks=len(measured),
            mean_nc=float(np.mean([result["nc"] for result in measured])) if measured else None,
            mean_ber=float(np.mean([result["ber"] for result in measured])) if measured else None,
            status="measured" if len(measured) == len(attack_specs) else (
                "partial" if measured else "extraction_failed"
            ),
        )
        if measured:
            eligible.append((trial, embedding))

    recommended = None
    if eligible:
        best_trial, best_embedding = max(
            eligible,
            key=lambda candidate: (
                candidate[0]["measured_attacks"],
                candidate[0]["mean_nc"],
                -candidate[0]["mean_ber"],
                -candidate[0]["strength"],
            ),
        )
        recommended = {
            "strength": best_trial["strength"],
            "embedding": best_embedding,
        }

    return {
        "psnr_floor": psnr_floor,
        "trials": trials,
        "recommended_strength": recommended["strength"] if recommended else None,
        "recommended_embedding": recommended["embedding"] if recommended else None,
    }
