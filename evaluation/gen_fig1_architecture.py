import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

fig, ax = plt.subplots(figsize=(10, 7.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.2)
ax.axis('off')

def box(x, y, w, h, text, fc="#EAF1FB", ec="#2C5AA0", fontsize=9, weight='normal', zorder=2):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                        linewidth=1.4, edgecolor=ec, facecolor=fc, zorder=zorder)
    ax.add_patch(b)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fontsize,
             weight=weight, zorder=zorder+1, wrap=True)
    return (x, y, w, h)

def arrow(p1, p2, style='<->', color='#333333', lw=1.3, ls='-', text=None, text_dx=0, text_dy=0.08, fontsize=7.5):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=12, color=color, lw=lw, linestyle=ls, zorder=3)
    ax.add_patch(a)
    if text:
        mx, my = (p1[0]+p2[0])/2 + text_dx, (p1[1]+p2[1])/2 + text_dy
        ax.text(mx, my, text, fontsize=fontsize, ha='center', color='#222222', zorder=4,
                 bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85))

# ---------- Layer bands ----------
ax.add_patch(mpatches.Rectangle((0.15, 5.55), 9.7, 1.35, fc="#FBF3E7", ec="none", zorder=0))
ax.text(0.3, 6.72, "Field / OT Layer", fontsize=9.5, weight='bold', color="#8A5A00")

ax.add_patch(mpatches.Rectangle((0.15, 4.05), 9.7, 1.35, fc="#EFF7ED", ec="none", zorder=0))
ax.text(0.3, 5.22, "Edge Layer (Policy Enforcement Point)", fontsize=9.5, weight='bold', color="#1E6B33")

ax.add_patch(mpatches.Rectangle((0.15, 1.0), 9.7, 2.85, fc="#EAF1FB", ec="none", zorder=0))
ax.text(0.3, 3.68, "Blockchain Layer (Policy Decision Point — Besu QBFT, n = 4)", fontsize=9.5, weight='bold', color="#1B3E7A")

ax.add_patch(mpatches.Rectangle((0.15, 0.12), 9.7, 0.68, fc="#FBEAEA", ec="none", zorder=0))
ax.text(0.3, 0.63, "External / Enterprise Layer", fontsize=9.5, weight='bold', color="#8A1E1E")

# ---------- Field layer devices ----------
d1 = box(0.5, 5.85, 1.5, 0.65, "Vibration /\nTemp. Sensors", fc="#FFF7E6")
d2 = box(2.2, 5.85, 1.5, 0.65, "PLC\n(CNC control)", fc="#FFF7E6")
d3 = box(3.9, 5.85, 1.5, 0.65, "SCADA / HMI\nStation", fc="#FFF7E6")
d4 = box(5.6, 5.85, 1.7, 0.65, "Actuators /\nOther Endpoints", fc="#FFF7E6")

# ---------- Edge layer ----------
gw = box(1.5, 4.3, 3.3, 0.85, "Zero-Trust Gateway (PEP)\nMQTT broker + REST bridge", fc="#E4F5E1", fontsize=9.5, weight='bold')
mon = box(5.2, 4.3, 2.4, 0.85, "Monitoring / IDS\nAnomaly & context evidence", fc="#E4F5E1", fontsize=9)

# ---------- Blockchain layer (contracts) ----------
c1 = box(0.6, 2.65, 2.3, 0.75, "IdentityRegistry.sol\nDID enrollment / revocation", fc="#DCE8FA", fontsize=8.6)
c2 = box(3.1, 2.65, 2.3, 0.75, "TrustManager.sol\nDynamic trust score (0-100)", fc="#DCE8FA", fontsize=8.6)
c3 = box(5.6, 2.65, 2.9, 0.75, "AccessControlManager.sol\nContext-aware policy decision (PDP)", fc="#DCE8FA", fontsize=8.6)

v1 = box(0.6, 1.25, 1.9, 1.0, "Validator 1\nPlant Operator", fc="#C9DAF5", fontsize=8.3)
v2 = box(2.7, 1.25, 1.9, 1.0, "Validator 2\nOEM", fc="#C9DAF5", fontsize=8.3)
v3 = box(4.8, 1.25, 1.9, 1.0, "Validator 3\nAuditor", fc="#C9DAF5", fontsize=8.3)
v4 = box(6.9, 1.25, 1.9, 1.0, "Validator 4\nRegulator", fc="#C9DAF5", fontsize=8.3)
ax.text(4.75, 1.15, "QBFT consensus  (f = 1 fault tolerated, 2 s block period)", fontsize=7.8, ha='center', style='italic', color='#333')

# ---------- External layer ----------
ext = box(3.4, 0.2, 3.3, 0.5, "OEM Predictive-Maintenance Cloud Service", fc="#F8DDDD", fontsize=8.6)

# ---------- Arrows: telemetry field -> edge ----------
for d in [d1, d2, d3, d4]:
    arrow((d[0]+d[2]/2, d[1]), (gw[0]+gw[2]*0.6, gw[1]+gw[3]), style='-|>', color='#8A5A00', lw=1.0)

arrow((gw[0]+gw[2], gw[1]+gw[3]*0.5), (mon[0], mon[1]+mon[3]*0.5), style='<|-|>', text="evidence", fontsize=7)

# Edge -> blockchain contracts (access request / decision)
arrow((gw[0]+gw[2]*0.3, gw[1]), (c3[0]+c3[2]*0.4, c3[1]+c3[3]), style='<|-|>', color='#1B3E7A', lw=1.4,
      text="checkAccess() / AccessDecision", text_dx=-1.4, text_dy=0.05, fontsize=7.3)
arrow((mon[0]+mon[2]*0.4, mon[1]), (c2[0]+c2[2]*0.7, c2[1]+c2[3]), style='-|>', color='#1B3E7A', lw=1.2,
      text="reportEvidence()", text_dx=0.9, text_dy=0.05, fontsize=7)

# Contract interlinks
arrow((c1[0]+c1[2], c1[1]+c1[3]*0.5), (c2[0], c2[1]+c2[3]*0.5), style='-|>', color='#555', lw=1.0)
arrow((c2[0]+c2[2], c2[1]+c2[3]*0.5), (c3[0], c3[1]+c3[3]*0.5), style='-|>', color='#555', lw=1.0)

# Contracts -> validators (deployed on / replicated across)
for v in [v1, v2, v3, v4]:
    arrow((v[0]+v[2]/2, v[1]+v[3]), (v[0]+v[2]/2, c1[1]), style='-', color='#8FA8CE', lw=0.8, ls=':')

# External -> edge gateway (remote access request)
arrow((ext[0]+ext[2]*0.5, ext[1]+ext[3]), (gw[0]+gw[2]*0.85, gw[1]), style='<|-|>', color='#8A1E1E', lw=1.3,
      text="remote firmware/setpoint request", text_dx=0.0, text_dy=0.1, fontsize=6.8)

ax.text(5, 7.05, "Blockchain-Based Zero-Trust Architecture for IIoT — System Overview",
         fontsize=12, weight='bold', ha='center')

plt.tight_layout()
plt.savefig('figures/fig1_architecture.png', dpi=220, bbox_inches='tight', facecolor='white')
print("saved")
