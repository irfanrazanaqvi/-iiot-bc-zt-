"""Fig. 1 (architecture) and Fig. 2 (request workflow), academic block-diagram style, 600 dpi.
   python3 evaluation/gen_paper_figures_diagrams.py"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paper_style import *
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch

def box(ax, x, y, w, h, text, fc="white", ec=INK, fs=6.2, lw=0.6, weight="normal", style="round,pad=0,rounding_size=0.03", ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=ec, lw=lw, ls=ls, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight=weight, color=INK, zorder=4, linespacing=1.15)

def arrow(ax, p, q, text=None, ls="-", color=INK, both=False, fs=5.6, rad=0.0, tpos=0.5, toff=(0, 0.045), ha="center", lw=0.6):
    a = FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=5, lw=lw, ls=ls, color=color, zorder=5,
                        connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0)
    ax.add_patch(a)
    if text:
        x = p[0] + (q[0] - p[0]) * tpos + toff[0]; y = p[1] + (q[1] - p[1]) * tpos + toff[1]
        ax.text(x, y, text, ha=ha, va="bottom", fontsize=fs, color=INK, zorder=6, style="italic")

# ------------------------------------------------------------------------------------------------
def fig1():
    fig = plt.figure(figsize=(W1, 3.45)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W1); ax.set_ylim(0, 3.45); ax.axis("off")
    FS, FT, FA = 6.4, 6.9, 6.1   # box text, layer title, annotation (pt)
    def layer(y, h, title, fc):
        ax.add_patch(Rectangle((0.03, y), W1 - 0.06, h, fc=fc, ec="#8A8A8A", lw=0.5, zorder=1))
        ax.text(0.08, y + h - 0.035, title, ha="left", va="top", fontsize=FT, fontweight="bold", color=INK, zorder=2)
    layer(2.80, 0.63, "Field / OT layer", "#F2F2F2")
    layer(1.98, 0.76, "Edge layer", "#EAF1E6")
    layer(0.62, 1.30, "Blockchain layer (Besu)", "#E3EDF7")
    layer(0.03, 0.53, "External layer", "#F7EFE4")
    for i, t in enumerate(["Vibration /\ntemp. sensors", "PLC\n(CNC control)", "SCADA /\nHMI station", "Actuators /\nendpoints"]):
        box(ax, 0.09 + i * 0.83, 2.83, 0.76, 0.31, t, fs=FS)
    box(ax, 0.10, 2.03, 1.20, 0.47, "Monitoring / IDS\nanomaly evidence", fs=FS)
    box(ax, 1.78, 2.03, 1.52, 0.47, "Zero-trust gateway (PEP)\nMQTT broker, REST bridge", weight="bold", fs=FS)
    cw = 1.05
    for i, t in enumerate(["IdentityRegistry\nDID, revocation", "TrustManager\nscore 0 to 100", "AccessControl (PDP)\ncontext policy"]):
        box(ax, 0.08 + i * 1.12, 1.19, cw, 0.42, t, fs=FS)
    arrow(ax, (1.13, 1.40), (1.20, 1.40)); arrow(ax, (2.25, 1.40), (2.32, 1.40))
    for i, t in enumerate(["V1 plant\noperator", "V2 OEM", "V3 auditor", "V4 regulator"]):
        box(ax, 0.09 + i * 0.83, 0.68, 0.76, 0.30, t, fc="#C9DDF0", fs=FS)
    ax.text(W1 / 2, 1.07, "QBFT consensus: 4 validators, f = 1, 2 s block period", ha="center", va="center", fontsize=FA, style="italic", zorder=4)
    box(ax, 0.80, 0.08, 1.75, 0.36, "OEM predictive-maintenance\ncloud service", fs=FS)
    arrow(ax, (2.30, 2.83), (2.30, 2.50), None); ax.text(2.36, 2.67, "telemetry, requests", ha="left", va="center", fontsize=FA, style="italic", zorder=6)
    arrow(ax, (1.78, 2.265), (1.30, 2.265), None, both=True); ax.text(1.54, 2.29, "evidence", ha="center", va="bottom", fontsize=FA, style="italic", zorder=6)
    arrow(ax, (2.72, 2.03), (2.72, 1.61), None, both=True); ax.text(2.77, 1.80, "checkAccess()", ha="left", va="center", fontsize=FA, style="italic", zorder=6)
    arrow(ax, (1.25, 2.03), (1.25, 1.61), None); ax.text(1.30, 1.80, "reportEvidence()", ha="left", va="center", fontsize=FA, style="italic", zorder=6)
    ax.plot([2.55, 3.395, 3.395], [0.26, 0.26, 2.265], color="#5A5A5A", lw=0.6, ls=(0, (3, 2)), zorder=5)
    arrow(ax, (3.395, 2.265), (3.30, 2.265), None, color="#5A5A5A")
    ax.text(2.62, 0.30, "remote request", fontsize=FA, style="italic", ha="left", va="bottom", zorder=6)
    save(fig, "fig1_architecture")

# ------------------------------------------------------------------------------------------------
def fig2():
    from matplotlib.patches import Circle
    H = 2.75
    FL, FH, FN = 6.5, 6.3, 6.0
    fig = plt.figure(figsize=(W1, H)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W1); ax.set_ylim(0, H); ax.axis("off")
    X = [0.38, 1.04, 1.72, 2.38, 3.04]
    heads = [("IIoT\ndevice", "#F2F2F2", "#8A8A8A"), ("Gateway\n(PEP)", "#DDEBD5", "#5E8C4A"),
             ("Identity\nRegistry", "#D3E4F5", "#2F6EA8"), ("Trust\nManager", "#D3E4F5", "#2F6EA8"), ("Access\nControl (PDP)", "#D3E4F5", "#2F6EA8")]
    bot = 0.44
    ys = [2.01 - 0.215 * i for i in range(8)]
    for i0, lab in [(1, "identity"), (3, "trust"), (5, "policy")]:
        yb = ys[i0 + 1] - 0.06; yt = ys[i0] + 0.15
        ax.add_patch(Rectangle((0.02, yb), W1 - 0.04, yt - yb, fc="#F1F5FA", ec="none", zorder=0))
        ax.text(W1 - 0.05, yb + 0.02, lab, ha="right", va="bottom", fontsize=FN, color="#4A5A6A", style="italic", zorder=1)
    for x, (l, fc, ec) in zip(X, heads):
        ax.add_patch(FancyBboxPatch((x - 0.31, 2.27), 0.62, 0.42, boxstyle="round,pad=0,rounding_size=0.04", fc=fc, ec=ec, lw=0.7, zorder=3))
        ax.text(x, 2.48, l, ha="center", va="center", fontsize=FH, color=INK, zorder=4, linespacing=1.1, fontweight="bold" if x == X[1] else "normal")
        ax.plot([x, x], [2.27, bot], color="#9A9A9A", lw=0.5, ls=(0, (1, 2)), zorder=1)
    ax.add_patch(Rectangle((X[1] - 0.03, bot + 0.04), 0.06, 2.27 - bot - 0.08, fc="#5E8C4A", ec="#3F6431", lw=0.4, zorder=3, alpha=0.9))
    steps = [(0, 1, "request", False), (1, 2, "isActive(device)?", False), (2, 1, "valid / revoked", True),
             (1, 3, "getScore(device)", False), (3, 1, "trust score", True),
             (1, 4, "checkAccess(device, resource, action)", False), (4, 1, "AccessDecision event", True), (1, 0, "allow / deny", True)]
    def badge(x, y, n, col):
        ax.add_patch(Circle((x, y), 0.058, fc=col, ec="none", zorder=7))
        ax.text(x, y, str(n), ha="center", va="center", fontsize=5.6, color="white", fontweight="bold", zorder=8)
    for n, ((s_, t_, lab, ret), y) in enumerate(zip(steps, ys), 1):
        d = 1 if t_ > s_ else -1
        xs = X[s_] + (0.03 * d if s_ == 1 else 0); xt = X[t_] - (0.03 * d if t_ == 1 else 0)
        col = "#2F6EA8" if ret else INK
        ax.add_patch(FancyArrowPatch((xs, y), (xt, y), arrowstyle="-|>", mutation_scale=5.5, lw=0.8, color=col,
                                     ls=(0, (3, 1.6)) if ret else "-", zorder=5, shrinkA=0, shrinkB=0))
        xl = X[0] + 0.16 if n in (1, 8) else X[1] + 0.19
        badge(xl - 0.08, y + 0.095, n, col)
        ax.text(xl, y + 0.04, lab, ha="left", va="bottom", fontsize=FL, color=col, zorder=6)
    ax.add_patch(FancyBboxPatch((1.17, 0.04), 2.16, 0.31, boxstyle="round,pad=0,rounding_size=0.04", fc="#FFF6DC", ec="#B08900", lw=0.6, zorder=4))
    ax.text(2.25, 0.195, "Monitoring / IDS reports evidence to\nTrustManager; the new score applies\nto the next request only", ha="center", va="center", fontsize=5.9, color=INK, zorder=5, linespacing=1.1)
    badge(1.17, 0.35, 9, "#B08900")
    ax.plot([X[3], X[3]], [bot, 0.35], color="#B08900", lw=0.6, ls=(0, (1, 1.5)), zorder=2)
    ax.text(0.05, 0.20, "Steps 1 to 8\nrepeat for every\nrequest. Dashed:\nreturn.", ha="left", va="center", fontsize=FN, color=INK, style="italic", linespacing=1.1)
    save(fig, "fig2_workflow")

fig1(); fig2(); print("done")
