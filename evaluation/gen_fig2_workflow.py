import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

fig, ax = plt.subplots(figsize=(10, 6.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 8.6)
ax.axis('off')

actors = [
    ("IIoT Device /\nOEM Requester", 0.8),
    ("ZT Gateway\n(PEP)", 2.9),
    ("IdentityRegistry\n(chain)", 4.9),
    ("TrustManager\n(chain)", 6.6),
    ("AccessControlManager\n(chain, PDP)", 8.7),
]

for label, x in actors:
    b = FancyBboxPatch((x-0.85, 7.75), 1.7, 0.7, boxstyle="round,pad=0.02", ec="#2C5AA0", fc="#EAF1FB", lw=1.3)
    ax.add_patch(b)
    ax.text(x, 8.1, label, ha='center', va='center', fontsize=8)
    ax.plot([x, x], [0.3, 7.75], color='#999999', lw=1, ls='--', zorder=0)

steps = [
    (0.8, 2.9, 7.35, "1. Access request\n(resource, action)"),
    (2.9, 4.9, 6.85, "2. isActive(device)?"),
    (4.9, 2.9, 6.4, "3. identity valid / revoked"),
    (2.9, 6.6, 5.9, "4. getScore(device)"),
    (6.6, 2.9, 5.45, "5. current trust score"),
    (2.9, 8.7, 4.95, "6. checkAccess(device, resource, action)"),
    (8.7, 2.9, 4.15, "7. AccessDecision event\n(granted / denied + reason)"),
    (2.9, 0.8, 3.55, "8. enforce decision\n(allow / deny at PEP)"),
]

for x1, x2, y, label in steps:
    direction = '-|>' if x2 > x1 else '<|-'
    a = FancyArrowPatch((x1, y), (x2, y), arrowstyle='-|>', mutation_scale=11, color='#1B3E7A', lw=1.2)
    ax.add_patch(a)
    mx = (x1+x2)/2
    ax.text(mx, y+0.13, label, ha='center', fontsize=7.3,
             bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.9))

ax.text(2.9, 2.9, "9. Monitoring/IDS observes outcome\n→ reportEvidence() to TrustManager\n(trust score updated for NEXT request only)",
         ha='center', fontsize=7.6, style='italic',
         bbox=dict(boxstyle='round,pad=0.3', fc='#FFF7E6', ec='#8A5A00', lw=0.8))

ax.text(5, 2.05, "No session state persists — step 1 repeats independently for every subsequent request (continuous verification, Section 4.8)",
         ha='center', fontsize=8, weight='bold', color='#8A1E1E')

ax.text(5, 8.5, "Figure 2. Continuous Verification Security Workflow (single access-request cycle)",
         ha='center', fontsize=11, weight='bold')

plt.tight_layout()
plt.savefig('figures/fig2_workflow.png', dpi=220, bbox_inches='tight', facecolor='white')
print("saved")
