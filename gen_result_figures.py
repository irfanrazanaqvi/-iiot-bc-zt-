import csv
import matplotlib.pyplot as plt

def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

perf = read_csv('results/results_perf.csv')
cent = read_csv('results/results_centralized.csv')
cpu_mem = read_csv('results/results_cpu_mem.csv')
sec = read_csv('results/results_security.csv')

conc = [int(r['concurrency']) for r in perf]

# ---- Figure 3: Latency vs concurrency (Proposed vs Centralized ZT baseline) ----
fig, ax = plt.subplots(figsize=(5.2, 3.6))
ax.plot(conc, [float(r['latency_p50_ms']) for r in perf], marker='o', label='Proposed (p50)', color='#1B3E7A')
ax.plot(conc, [float(r['latency_p95_ms']) for r in perf], marker='s', label='Proposed (p95)', color='#2C5AA0', ls='--')
ax.plot([int(r['concurrency']) for r in cent], [float(r['latency_p95_ms']) for r in cent],
        marker='^', label='Centralized ZT baseline (p95)', color='#B04A4A')
ax.set_xlabel('Concurrent devices')
ax.set_ylabel('Authorization latency (ms)')
ax.set_title('Figure 3. Authorization Latency vs. Concurrency')
ax.legend(fontsize=7.5)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figures/fig3_latency.png', dpi=220, facecolor='white')
plt.close()

# ---- Figure 4: Throughput vs concurrency ----
fig, ax = plt.subplots(figsize=(5.2, 3.6))
ax.plot(conc, [float(r['throughput_rps']) for r in perf], marker='o', color='#1E6B33', label='Proposed (Besu QBFT)')
ax.plot([int(r['concurrency']) for r in cent], [float(r['throughput_rps']) for r in cent],
        marker='^', color='#B04A4A', label='Centralized ZT baseline')
ax.set_xlabel('Concurrent devices')
ax.set_ylabel('Throughput (requests/s)')
ax.set_title('Figure 4. Gateway Throughput vs. Concurrency')
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figures/fig4_throughput.png', dpi=220, facecolor='white')
plt.close()

# ---- Figure 5: CPU/Memory utilization ----
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.4))
c2 = [int(r['concurrency']) for r in cpu_mem]
ax1.plot(c2, [float(r['validator_cpu_pct']) for r in cpu_mem], marker='o', label='Validator (avg of 4)', color='#1B3E7A')
ax1.plot(c2, [float(r['gateway_cpu_pct']) for r in cpu_mem], marker='s', label='Gateway (PEP)', color='#1E6B33')
ax1.set_xlabel('Concurrent devices'); ax1.set_ylabel('CPU utilization (%)')
ax1.set_title('(a) CPU'); ax1.legend(fontsize=7.5); ax1.grid(alpha=0.3)

ax2.plot(c2, [float(r['validator_mem_mb']) for r in cpu_mem], marker='o', label='Validator (avg of 4)', color='#1B3E7A')
ax2.plot(c2, [float(r['gateway_mem_mb']) for r in cpu_mem], marker='s', label='Gateway (PEP)', color='#1E6B33')
ax2.set_xlabel('Concurrent devices'); ax2.set_ylabel('Memory (MB)')
ax2.set_title('(b) Memory'); ax2.legend(fontsize=7.5); ax2.grid(alpha=0.3)
fig.suptitle('Figure 5. Resource Utilization vs. Concurrency', y=1.03)
plt.tight_layout()
plt.savefig('figures/fig5_cpu_mem.png', dpi=220, bbox_inches='tight', facecolor='white')
plt.close()

# ---- Figure 6: Security — denial/detection rate per attack scenario across architectures ----
fig, ax = plt.subplots(figsize=(6.6, 3.8))
labels = [r['attack_scenario'] for r in sec]
archs = ["No ACL (B0)", "Static RBAC (B1)", "Centralized ZT (B2)", "Proposed"]
colors = ["#B04A4A", "#D8A648", "#5A8FBF", "#1E6B33"]
x = range(len(labels))
width = 0.2
for i, a in enumerate(archs):
    vals = [float(r[a]) for r in sec]
    ax.bar([xi + i*width for xi in x], vals, width=width, label=a, color=colors[i])
ax.set_xticks([xi + 1.5*width for xi in x])
ax.set_xticklabels([l.replace(' ', '\n', 1) for l in labels], fontsize=6.3, rotation=20, ha='right')
ax.set_ylabel('Correct denial rate')
ax.set_title('Figure 6. Attack Denial Rate by Architecture and Scenario')
ax.legend(fontsize=7, loc='lower right')
ax.set_ylim(0, 1.05)
ax.grid(alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig('figures/fig6_security.png', dpi=220, facecolor='white')
plt.close()

print("figures saved")
