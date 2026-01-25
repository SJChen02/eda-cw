#!/usr/bin/env python3
"""
final_results.py

1) Collect *_parse.out from all workers via ansible
2) Build final_results.csv
3) Build hits_output.csv and profile_output.csv

ALL outputs go into ./pipeline_output/
"""

import subprocess
import csv
from pathlib import Path
import sys
import math


INVENTORY = "./generate_inventory.py"

# Output directory
PIPELINE_OUTDIR = Path("pipeline_output")

FINAL_RESULTS = PIPELINE_OUTDIR / "final_results.csv"
HITS_OUT = PIPELINE_OUTDIR / "hits_output.csv"
PROFILE_OUT = PIPELINE_OUTDIR / "profile_output.csv"

HEADER = [
    "query_id",
    "best_hit",
    "best_evalue",
    "best_score",
    "score_mean",
    "score_std",
    "score_gmean",
]


def run_ansible_collect() -> list[str]:
    """
    Use ansible to grab line 2 of every *_parse.out on all workers.
    Returns list of CSV data lines.
    """
    cmd = [
        "ansible",
        "-i", INVENTORY,
        "workers",
        "-m", "shell",
        "-a", "awk 'FNR==2' /data/results/*/*_parse.out 2>/dev/null || true",
    ]

    print("Running ansible to collect *_parse.out from workers...")
    p = subprocess.run(cmd, capture_output=True, text=True)

    if p.returncode != 0:
        print("ERROR: ansible command failed", file=sys.stderr)
        print(p.stderr, file=sys.stderr)
        sys.exit(1)

    lines = []
    for line in p.stdout.splitlines():
        # Filter out ansible noise, keep CSV-looking lines
        if "," in line and not line.strip().startswith(("10.", "|", "rc=")):
            lines.append(line.strip())

    return lines


def write_final_results(data_lines: list[str]) -> None:
    print(f"Writing {FINAL_RESULTS} with {len(data_lines)} rows...")
    with FINAL_RESULTS.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for line in data_lines:
            parts = [x.strip() for x in line.split(",")]
            if len(parts) >= 7:
                w.writerow(parts[:7])


import math

def to_float(x: str):
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def format_outputs():
    rows = []

    with FINAL_RESULTS.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    # Ensure output dir exists
    PIPELINE_OUTDIR.mkdir(parents=True, exist_ok=True)

    # ---- hits_output.csv ----
    with HITS_OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fasta_id", "best_hit_id"])
        for r in rows:
            if r["query_id"] and r["best_hit"]:
                w.writerow([r["query_id"], r["best_hit"]])

    # ---- profile_output.csv ----
    stds = []
    gmeans = []

    for r in rows:
        s = to_float(r.get("score_std", ""))
        g = to_float(r.get("score_gmean", ""))
        if s is not None:
            stds.append(s)
        if g is not None:
            gmeans.append(g)

    ave_std = sum(stds) / len(stds) if stds else 0.0
    ave_gmean = sum(gmeans) / len(gmeans) if gmeans else 0.0

    with PROFILE_OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ave_std", "ave_gmean"])
        w.writerow([f"{ave_std:.2f}", f"{ave_gmean:.2f}"])

    print(f"Wrote {HITS_OUT}")
    print(f"Wrote {PROFILE_OUT}")
    print(f"Profile averages: ave_std={ave_std:.2f}, ave_gmean={ave_gmean:.2f}")


def main():
    # Ensure output dir exists early
    PIPELINE_OUTDIR.mkdir(parents=True, exist_ok=True)

    data_lines = run_ansible_collect()

    if not data_lines:
        print("WARNING: No *_parse.out data found on workers.")
        print("Did you run the pipeline?")
        sys.exit(1)

    write_final_results(data_lines)
    format_outputs()

    print("\nDONE.")
    print(f"- final_results.csv -> {FINAL_RESULTS.resolve()}")
    print(f"- hits_output.csv   -> {HITS_OUT.resolve()}")
    print(f"- profile_output.csv-> {PROFILE_OUT.resolve()}")


if __name__ == "__main__":
    main()
