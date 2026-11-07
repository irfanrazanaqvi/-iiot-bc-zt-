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
    def layer(y, h, title, fc):
        ax.add_patch(Rectangle((0.03, y), W1 - 0.06, h, fc=fc, ec="#8A8A8A", lw=0.5, zorder=1))
        ax.text(0.08, y + h - 0.04, title, ha="left", va="top", fontsize=6.2, fontweight="bold", color=INK, zorder=2)
    layer(2.80, 0.63, "Field / OT layer", "#F2F2F2")
    layer(1.98, 0.76, "Edge layer", "#EAF1E6")
    layer(0.62, 1.30, "Blockchain layer (Besu)", "#E3EDF7")
    layer(0.03, 0.53, "External layer", "#F7EFE4")
    # field devices
    for i, t in enumerate(["Vibration /\ntemp. sensors", "PLC\n(CNC control)", "SCADA /\nHMI station", "Actuators /\nendpoints"]):
        box(ax, 0.17 + i * 0.80, 2.84, 0.72, 0.30, t, fs=5.6)
    # edge
    box(ax, 0.22, 2.04, 1.23, 0.48, "Monitoring / IDS\nanomaly evidence", fs=5.9)
    box(ax, 1.75, 2.04, 1.55, 0.48, "Zero-trust gateway (PEP)\nMQTT broker, REST bridge", fc="white", weight="bold", fs=6.0)
    # contracts
    cw = 1.00
    for i, t in enumerate(["IdentityRegistry\nDID, revocation", "TrustManager\nscore 0 to 100", "AccessControl (PDP)\ncontext policy"]):
        box(ax, 0.12 + i * 1.10, 1.22, cw, 0.40, t, fc="white", fs=5.5)
    arrow(ax, (1.12, 1.42), (1.22, 1.42)); arrow(ax, (2.22, 1.42), (2.32, 1.42))
    for i, t in enumerate(["V1 plant\noperator", "V2 OEM", "V3 auditor", "V4 regulator"]):
        box(ax, 0.17 + i * 0.80, 0.72, 0.72, 0.30, t, fc="#C9DDF0", fs=5.5)
    ax.text(W1 / 2, 1.08, "QBFT consensus: 4 validators, f = 1, 2 s block period", ha="center", va="center", fontsize=5.5, style="italic", zorder=4)
    box(ax, 0.90, 0.09, 1.65, 0.34, "OEM predictive-maintenance\ncloud service", fc="white", fs=5.8)
    # flows
    arrow(ax, (2.52, 2.84), (2.52, 2.52), "telemetry, requests", toff=(0.04, -0.08), ha="left", fs=5.4)
    arrow(ax, (1.75, 2.28), (1.45, 2.28), None, both=True); ax.text(1.60, 2.31, "evidence", ha="center", va="bottom", fontsize=5.2, style="italic", zorder=6)
    arrow(ax, (2.70, 2.04), (2.70, 1.62), None, both=True); ax.text(2.75, 1.78, "checkAccess()", ha="left", va="center", fontsize=5.4, style="italic", zorder=6)
    arrow(ax, (1.38, 2.04), (1.38, 1.62), None); ax.text(1.43, 1.78, "reportEvidence()", ha="left", va="center", fontsize=5.4, style="italic", zorder=6)
    ax.plot([2.55, 3.38, 3.38], [0.26, 0.26, 2.28], color="#5A5A5A", lw=0.6, ls=(0, (3, 2)), zorder=5)
    arrow(ax, (3.38, 2.28), (3.30, 2.28), None, color="#5A5A5A")
    ax.text(2.60, 0.29, "remote\nrequest", fontsize=5.2, style="italic", ha="left", va="bottom", zorder=6)
    save(fig, "fig1_architecture")

# ------------------------------------------------------------------------------------------------
def fig2():
    fig = plt.figure(figsize=(W1, 2.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W1); ax.set_ylim(0, 2.6); ax.axis("off")
    X = [0.34, 1.02, 1.72, 2.38, 3.07]; names = ["IIoT device /\nrequester", "Gateway\n(PEP)", "Identity-\nRegistry", "Trust-\nManager", "Access-\nControl (PDP)"]
    top, bot = 2.20, 0.34
    for x, n in zip(X, names):
        box(ax, x - 0.29, 2.22, 0.58, 0.33, n, fc="#EEF3F9", fs=5.5, style="square,pad=0")
        ax.plot([x, x], [top, bot], color="#7A7A7A", lw=0.5, ls=(0, (3, 2)), zorder=2)
    ax.add_patch(Rectangle((X[1] - 0.035, 0.46), 0.07, 1.70, fc="white", ec=INK, lw=0.5, zorder=3))  # activation of the PEP
    steps = [  # (from, to, label, dashed)
        (0, 1, "1  access request", False), (1, 2, "2  isActive(device)?", False), (2, 1, "3  valid / revoked", True),
        (1, 3, "4  getScore(device)", False), (3, 1, "5  current trust score", True),
        (1, 4, "6  checkAccess(device, resource, action)", False), (4, 1, "7  AccessDecision event", True), (1, 0, "8  allow / deny", True)]
    y = 2.03
    for s, t, lab, dashed in steps:
        xs, xt = X[s], X[t]; d = 1 if t > s else -1
        arrow(ax, (xs + 0.035 * d, y), (xt - 0.035 * d if t == 1 else xt, y), None, ls=(0, (3, 1.5)) if dashed else "-", lw=0.7)
        g = (s == 1 or t == 1) and max(s, t) > 1
        ax.text(X[1] + 0.07 if g else (xs + xt) / 2, y + 0.035, lab, ha="left" if g else "center", va="bottom", fontsize=5.7, zorder=6)
        y -= 0.215
    # monitoring note
    box(ax, 1.30, 0.30, 1.85, 0.27, "9  Monitoring / IDS: reportEvidence() to TrustManager;\nthe new score applies to the next request only", fc="#FFF8E8", ec="#8A6D00", fs=5.2, style="square,pad=0")
    ax.text(W1 / 2, 0.10, "Every request repeats steps 1 to 8 independently; no session state persists.", ha="center", va="center", fontsize=5.8, style="italic")
    save(fig, "fig2_workflow")

fig1(); fig2(); print("done")
