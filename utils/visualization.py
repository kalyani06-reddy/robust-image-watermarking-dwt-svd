import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def save_attack_plot(labels, values, filename, title, ylabel):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values, color=['#2563eb', '#7c3aed', '#0ea5e9', '#f59e0b', '#10b981'])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    plt.tight_layout()
    fig.savefig(filename, dpi=150)
    plt.close(fig)
    return filename
