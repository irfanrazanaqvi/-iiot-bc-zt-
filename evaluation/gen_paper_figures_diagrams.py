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
    from matplotlib.patches import Circle
    H = 2.6
    fig = plt.figure(figsize=(W1, H)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W1); ax.set_ylim(0, H); ax.axis("off")
    X = [0.40, 1.05, 1.74, 2.38, 3.04]
    heads = [("IIoT device /", "requester", "#F2F2F2", "#8A8A8A"), ("Gateway", "(PEP)", "#DDEBD5", "#5E8C4A"),
             ("Identity-", "Registry", "#D3E4F5", "#2F6EA8"), ("Trust-", "Manager", "#D3E4F5", "#2F6EA8"), ("AccessControl", "(PDP)", "#D3E4F5", "#2F6EA8")]
    bot = 0.46
    ys = [1.98 - 0.205 * i for i in range(8)]
    for i0, lab in [(1, "identity"), (3, "trust"), (5, "policy")]:
        yb = ys[i0 + 1] - 0.05; yt = ys[i0] + 0.13
        ax.add_patch(Rectangle((0.02, yb), W1 - 0.04, yt - yb, fc="#F1F5FA", ec="none", zorder=0))
        ax.text(W1 - 0.05, yb + 0.02, lab, ha="right", va="bottom", fontsize=5.0, color="#5A6B7B", style="italic", zorder=1)
    for x, (l1, l2, fc, ec) in zip(X, heads):
        ax.add_patch(FancyBboxPatch((x - 0.30, 2.24), 0.60, 0.30, boxstyle="round,pad=0,rounding_size=0.04", fc=fc, ec=ec, lw=0.7, zorder=3))
        ax.text(x, 2.39, l1 + "\n" + l2, ha="center", va="center", fontsize=5.3, color=INK, zorder=4, linespacing=1.1, fontweight="bold" if x == X[1] else "normal")
        ax.plot([x, x], [2.24, bot], color="#9A9A9A", lw=0.5, ls=(0, (1, 2)), zorder=1)
    ax.add_patch(Rectangle((X[1] - 0.03, bot + 0.04), 0.06, 2.24 - bot - 0.08, fc="#5E8C4A", ec="#3F6431", lw=0.4, zorder=3, alpha=0.9))
    steps = [(0, 1, "access request", False), (1, 2, "isActive(device)?", False), (2, 1, "valid / revoked", True),
             (1, 3, "getScore(device)", False), (3, 1, "current trust score", True),
             (1, 4, "checkAccess(device, resource, action)", False), (4, 1, "AccessDecision event", True), (1, 0, "allow / deny", True)]
    def badge(x, y, n, col):
        ax.add_patch(Circle((x, y), 0.052, fc=col, ec="none", zorder=7))
        ax.text(x, y, str(n), ha="center", va="center", fontsize=4.6, color="white", fontweight="bold", zorder=8)
    for n, ((s_, t_, lab, ret), y) in enumerate(zip(steps, ys), 1):
        d = 1 if t_ > s_ else -1
        xs = X[s_] + (0.03 * d if s_ == 1 else 0); xt = X[t_] - (0.03 * d if t_ == 1 else 0)
        col = "#2F6EA8" if ret else INK
        ax.add_patch(FancyArrowPatch((xs, y), (xt, y), arrowstyle="-|>", mutation_scale=5.5, lw=0.75, color=col,
                                     ls=(0, (3, 1.6)) if ret else "-", zorder=5, shrinkA=0, shrinkB=0))
        xl = X[0] + 0.14 if n in (1, 8) else X[1] + 0.20
        badge(xl - 0.075, y + 0.085, n, col)
        ax.text(xl, y + 0.04, lab, ha="left", va="bottom", fontsize=5.6, color=col, zorder=6)
    ax.add_patch(FancyBboxPatch((1.18, 0.05), 2.12, 0.30, boxstyle="round,pad=0,rounding_size=0.04", fc="#FFF6DC", ec="#B08900", lw=0.6, zorder=4))
    ax.text(2.27, 0.20, "Monitoring / IDS: reportEvidence() to TrustManager;\nthe new score applies to the next request only", ha="center", va="center", fontsize=5.0, color=INK, zorder=5, linespacing=1.15)
    badge(1.18, 0.35, 9, "#B08900")
    ax.plot([X[3], X[3]], [bot, 0.35], color="#B08900", lw=0.6, ls=(0, (1, 1.5)), zorder=2)
    ax.text(0.05, 0.20, "Steps 1 to 8 repeat for\nevery request; no session\nstate. Solid: call; dashed: return.", ha="left", va="center", fontsize=4.7, color=INK, style="italic", linespacing=1.15)
    save(fig, "fig2_workflow")

fig1(); fig2(); print("done")
