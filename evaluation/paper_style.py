"""Shared academic figure style (IEEE single column = 3.45 in, double = 7.16 in; 600 dpi; PNG + vector PDF)."""
import pathlib, matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt

W1, W2 = 3.45, 7.16
mpl.rcParams.update({
    "font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 7, "axes.labelsize": 7.5, "axes.titlesize": 7.5,
    "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.3, "legend.frameon": False,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "xtick.minor.size": 1.5, "ytick.minor.size": 1.5, "lines.linewidth": 1.0, "lines.markersize": 3.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#D0D0D0",
    "grid.linewidth": 0.4, "grid.linestyle": ":", "axes.axisbelow": True,
    "figure.dpi": 150, "savefig.dpi": 600, "savefig.facecolor": "white", "pdf.fonttype": 42, "ps.fonttype": 42,
    "figure.constrained_layout.use": False,
})

# Colour-blind safe (Okabe-Ito, darkened where needed so every colour has >= 3:1 contrast on white); each also has its own marker/hatch
ARCH = {  # key: (label, colour, marker, linestyle, hatch)
    "b0":  ("B0 no control",        "#7F7F7F", "o", (0, (1, 1)),   ""),
    "b1":  ("B1 static RBAC",       "#B36B00", "s", (0, (4, 1.5)), "//"),
    "b2":  ("B2 centralized ZT",    "#D55E00", "^", (0, (3, 1, 1, 1)), "\\\\"),
    "b3":  ("B3 hardened ZT",       "#B05A8C", "v", (0, (5, 1)),   "xx"),
    "b4":  ("B4 replicated ZT",     "#009E73", "P", (0, (2, 1)),   ".."),
    "bcz": ("BC-ZT (proposed)",     "#0072B2", "D", "-",           ""),
}
INK, MUTED = "#1A1A1A", "#555555"
OUT = pathlib.Path(__file__).resolve().parent / "figures_paper"; OUT.mkdir(exist_ok=True)

def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=600); fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)

def panel(ax, tag, x=-0.02, y=1.04):
    ax.text(x, y, tag, transform=ax.transAxes, fontsize=8, fontweight="bold", ha="right", va="bottom")
