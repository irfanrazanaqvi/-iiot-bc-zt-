#!/usr/bin/env python3
"""Offline studies (no chain, no cloud) built on the contract's trust law.

  Study 1  decay calibration: sensitivity of (kappa, tau, theta, evidence interval E)
  Study 2  telemetry-derived evidence: EWMA detector on synthetic telemetry feeds
           negative evidence to the same law (replaces the injected A5 evidence)

The trust law is Eq. (1)/(2) of the paper, exactly as TrustManager.sol implements it:
    T(t) = max(0, T_last - kappa * floor((t - t_last) / tau)),  evidence: T = clamp(T + delta, 0, 100)
Everything here is a simulation with synthetic telemetry and stated assumptions.

  python3 experiments/offline_calibration.py --out evaluation/results_offline
"""
import argparse, json, math, pathlib
import numpy as np, pandas as pd

HOUR, DAY = 3600.0, 86400.0
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="evaluation/results_offline")
ap.add_argument("--seed", type=int, default=7)
A = ap.parse_args()
OUT = pathlib.Path(A.out); OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(A.seed)


def decayed(T_last, dt, kappa, tau):
    return max(0.0, T_last - kappa * math.floor(dt / tau))


# ----------------------------------------------------------------------------------------
# Study 1: decay calibration
# ----------------------------------------------------------------------------------------
D_POS, T_START, T_COMP = 5, 80, 90   # healthy attestation +5; healthy starts at 80; compromised device was at 90
SIM_DAYS, REQ_GAP = 30, 600.0        # 30 simulated days, one access request per 10 min per device
rows = []
for kappa in (1, 2, 5, 10):
    for tau_h in (1, 6, 24):
        tau = tau_h * HOUR
        for theta in (40, 70):
            # silent compromised device: no evidence ever arrives; first denied request after n steps
            n = int((T_COMP - theta) // kappa) + 1
            t_deny_h = n * tau_h
            for E_h in (1, 6, 24):          # mean interval between positive evidence events (Poisson)
                fd, tot = 0, 0
                for rep in range(20):
                    t, T, tl = 0.0, float(T_START), 0.0
                    next_ev = rng.exponential(E_h * HOUR)
                    while t < SIM_DAYS * DAY:
                        t += REQ_GAP
                        while next_ev <= t:                       # apply evidence events that occurred
                            T = min(100.0, decayed(T, next_ev - tl, kappa, tau) + D_POS); tl = next_ev
                            next_ev += rng.exponential(E_h * HOUR)
                        if t > 2 * DAY:                           # skip a 2-day warm-up
                            tot += 1; fd += decayed(T, t - tl, kappa, tau) < theta
                rows.append(dict(kappa=kappa, tau_h=tau_h, theta=theta, E_h=E_h,
                                 time_to_deny_h=t_deny_h, false_deny=fd / tot))
S1 = pd.DataFrame(rows); S1.to_csv(OUT / "decay_sensitivity.csv", index=False)

# ----------------------------------------------------------------------------------------
# Study 2: telemetry-derived evidence
# ----------------------------------------------------------------------------------------
FS = 10.0                     # one sample every 10 s (vibration RMS of a CNC spindle, arbitrary units)
MU, SIG, RHO = 1.0, 0.10, 0.8  # healthy level, noise sd, AR(1) autocorrelation
LAMBDA = 0.1                  # EWMA smoothing
BASE_N = 360                  # first hour is used to estimate the baseline
D_NEG, MIN_GAP = -20, 60.0    # each alarm reports -20 trust, at most one report per 60 s per device
KAPPA, TAU = 2, DAY


def stream(n, shift=0.0, vscale=1.0, ramp=0.0, onset=None):
    e = np.empty(n); e[0] = rng.normal(0, SIG)
    w = rng.normal(0, SIG * math.sqrt(1 - RHO ** 2), n)
    for i in range(1, n): e[i] = RHO * e[i - 1] + w[i]
    x = MU + e
    if onset is not None:
        k = np.arange(n) - onset
        a = k >= 0
        x[a] = MU + vscale * e[a] + shift * SIG + ramp * SIG * (k[a] / 360.0)
    return x


def alarms(x, L):
    """EWMA of the standardized residual; alarm when |z_ewma| > L * sd_ewma.
    Mean, sd and the EWMA's own sd (which autocorrelation inflates) are all estimated from the first BASE_N samples."""
    m, s = x[:BASE_N].mean(), x[:BASE_N].std() + 1e-9
    z = (x - m) / s
    ew = np.empty(len(x)); e = 0.0
    for i in range(len(x)):
        e = LAMBDA * z[i] + (1 - LAMBDA) * e; ew[i] = e
    sd = ew[30:BASE_N].std() + 1e-9
    out = np.abs(ew) > L * sd
    out[:BASE_N] = False
    return out


def trust_after(alarm_idx, score0, theta, onset_i):
    """Apply -20 per rate-limited alarm; return seconds from onset to first denied request (None if never)."""
    T, last = float(score0), -1e9
    for i in alarm_idx:
        t = i * FS
        if t - last >= MIN_GAP:
            T = max(0.0, T + D_NEG); last = t
            if T < theta: return t - onset_i * FS + 2.0   # +2 s: one block for the evidence tx to finalize
    return None


MODES = {"mean shift +3 sd": dict(shift=3.0), "variance x3": dict(vscale=3.0), "drift 1 sd/hour": dict(ramp=1.0)}
res = []
N_TR, N_FA, DUR, ONSET = 100, 100, 720, 400    # 100 attack trials; 100 healthy device-days (8640 samples) per L
for L in (3.0, 4.0, 5.0, 6.0, 8.0):
    # false alarms: healthy device-days
    n_fa, t_fa, fd = 0, 0, {40: 0, 70: 0}
    for _ in range(N_FA):
        x = stream(8640); al = np.where(alarms(x, L))[0]
        # count alarm *reports* (rate limited) and the resulting trust of a healthy device that also attests every 6 h
        rep, last, T, tl = [], -1e9, 80.0, 0.0
        for i in al:
            t = i * FS
            if t - last >= MIN_GAP: rep.append(t); last = t
        n_fa += len(rep)
        events = sorted([(t, D_NEG) for t in rep] + [(h * 6 * HOUR, D_POS) for h in range(1, 5)])
        den = {40: False, 70: False}
        for t, d in events:
            T = min(100.0, max(0.0, decayed(T, t - tl, KAPPA, TAU) + d)); tl = t
            for th in den: den[th] |= T < th
        for th in fd: fd[th] += den[th]
    for mode, kw in MODES.items():
        det, delay, den40, den70 = 0, [], [], []
        for _ in range(N_TR):
            x = stream(DUR, onset=ONSET, **kw); al = np.where(alarms(x, L))[0]
            first = [i for i in al if i >= ONSET]
            if first:
                det += 1; delay.append((first[0] - ONSET) * FS)
                den40.append(trust_after(first, 80, 40, ONSET)); den70.append(trust_after(first, 80, 70, ONSET))
        ok = lambda v: [a for a in v if a is not None]
        res.append(dict(L=L, mode=mode, detect_rate=det / N_TR,
                        detect_delay_s=float(np.median(delay)) if delay else np.nan,
                        false_reports_per_device_day=n_fa / N_FA,
                        healthy_denied_theta40=fd[40] / N_FA, healthy_denied_theta70=fd[70] / N_FA,
                        denied_after_s_theta40=float(np.median(ok(den40))) if ok(den40) else np.nan,
                        denied_after_s_theta70=float(np.median(ok(den70))) if ok(den70) else np.nan,
                        denied_frac_theta40=len(ok(den40)) / N_TR, denied_frac_theta70=len(ok(den70)) / N_TR))
S2 = pd.DataFrame(res); S2.to_csv(OUT / "telemetry_evidence.csv", index=False)

# ----------------------------------------------------------------------------------------
# summary + figure
# ----------------------------------------------------------------------------------------
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.2))
for E, mk, c in ((1, "o", "#1B3E7A"), (6, "s", "#C9A227"), (24, "^", "#B04A4A")):
    d = S1[(S1.theta == 70) & (S1.E_h == E)]
    a.scatter(d.time_to_deny_h / 24, 100 * d.false_deny, marker=mk, color=c, label=f"evidence every {E} h", alpha=.8)
dep = S1[(S1.kappa == 2) & (S1.tau_h == 24) & (S1.theta == 70)]
a.scatter(dep.time_to_deny_h / 24, 100 * dep.false_deny, s=140, facecolors="none", edgecolors="k", label="deployed (kappa=2, tau=1 d)")
a.set_xscale("log"); a.set_xlabel("Days until a silent compromise is denied"); a.set_ylabel("Healthy requests denied (%)")
a.set_title("(a) decay calibration, theta = 70", fontsize=8); a.legend(fontsize=6); a.grid(alpha=.3, which="both")
for mode, mk in zip(MODES, ("o", "s", "^")):
    d = S2[S2["mode"] == mode]
    b.plot(d.false_reports_per_device_day, 100 * d.detect_rate, marker=mk, label=mode)
b.set_xscale("symlog", linthresh=1e-1); b.set_xlabel("False alarm reports per healthy device-day"); b.set_ylabel("Attacks detected (%)")
b.set_title("(b) EWMA detector, threshold L swept 3 to 8", fontsize=8); b.legend(fontsize=6); b.grid(alpha=.3)
plt.tight_layout(); (OUT / "figures").mkdir(exist_ok=True); plt.savefig(OUT / "figures/fig8_offline.png", dpi=220, facecolor="white")

with open(OUT / "summary.md", "w") as f:
    f.write("# Offline calibration studies (simulation, synthetic telemetry)\n\n## Study 1: decay sensitivity (theta=70, deployed kappa=2, tau=1 d)\n\n")
    f.write(S1[(S1.theta == 70)].pivot_table(index=["kappa", "tau_h"], columns="E_h", values=["time_to_deny_h", "false_deny"]).round(3).to_markdown() + "\n\n")
    f.write("## Study 2: telemetry-derived evidence\n\n" + S2.round(3).to_markdown(index=False) + "\n")
print(open(OUT / "summary.md").read())
