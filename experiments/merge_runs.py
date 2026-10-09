"""Merge two run_all output folders: keep run1 rows for architectures NOT re-run, take run2 rows for the re-run ones.

Usage: python3 experiments/merge_runs.py <run1_dir> <run2_dir> <out_dir> <archs_taken_from_run2, comma separated>
meta.json (block statistics, deployment) comes from run2.  Both raw folders should be kept next to the merged one.
"""
import shutil, sys
from pathlib import Path

import pandas as pd

r1, r2, out = (Path(a) for a in sys.argv[1:4]); new = set(sys.argv[4].split(","))
out.mkdir(parents=True, exist_ok=True)
for f in ("perf_raw.csv", "openloop_raw.csv", "security_raw.csv", "revocation_raw.csv", "phases.csv"):
    a = pd.read_csv(r1 / f) if (r1 / f).exists() else pd.DataFrame()
    if len(a):
        a = a[~a.arch.isin(new)]
    b = pd.read_csv(r2 / f)
    m = pd.concat([a, b], ignore_index=True)
    m.to_csv(out / f, index=False)
    print(f, "run1 rows kept:", len(a), "| run2 rows:", len(b), "| merged:", len(m))
shutil.copy(r2 / "meta.json", out / "meta.json")
for f in ("decay_raw.csv", "scale_raw.csv"):
    for src in (r2, r1):
        if (src / f).exists():
            shutil.copy(src / f, out / f); break
