# task_dispatcher.py (run on the host)
import os
from Bio import SeqIO
from pipeline_tasks import run_one_protein

IDS_FILE = os.environ.get("IDS_FILE", "experiment_ids.txt")
FASTA_FILE = os.environ.get("FASTA_FILE", "/data/proteins/UP000000589_10090.fasta")

def load_target_ids(path: str) -> set[str]:
    ids = set()
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s:
                ids.add(s)
    return ids

def record_matches(record_id: str, targets: set[str]) -> bool:
    # match either full header id or any pipe-separated part
    if record_id in targets:
        return True
    parts = record_id.split("|")
    return any(p in targets for p in parts)

if __name__ == "__main__":
    targets = load_target_ids(IDS_FILE)
    print(f"Loaded {len(targets)} target IDs from {IDS_FILE}")
    print(f"Scanning FASTA: {FASTA_FILE}")

    submitted = 0
    for rec in SeqIO.parse(FASTA_FILE, "fasta"):
        if record_matches(rec.id, targets):
            run_one_protein.delay(rec.id, str(rec.seq))
            submitted += 1
            if submitted % 100 == 0:
                print(f"Submitted {submitted} tasks...")

    print(f"Done! Submitted {submitted} protein tasks.")
