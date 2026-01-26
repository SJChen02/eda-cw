# task_dispatcher.py (run on the host)
import os
from proteome_store import get_record
from pipeline_tasks import run_one_protein

# IDS_FILE = os.environ.get("IDS_FILE", "experiment_ids.txt")
IDS_FILE= "/tmp/ids_test.txt PROTEOME_DB=/data/proteome.db python3 /opt/protein_pipeline/task_dispatcher.py"

DB_PATH = os.environ.get("PROTEOME_DB", "/data/proteome.db")


def load_target_ids(path: str) -> list[str]:
    ids = []
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s:
                ids.append(s)
    # keep order, drop duplicates
    return list(dict.fromkeys(ids))


if __name__ == "__main__":
    targets = load_target_ids(IDS_FILE)
    print(f"Loaded {len(targets)} target IDs from {IDS_FILE}")
    print(f"Using SQLite DB: {DB_PATH}")

    submitted = 0
    missing = 0

    for pid in targets:
        rec = get_record(pid, db_path=DB_PATH)
        if not rec:
            missing += 1
            # keep this message (useful in viva)
            print(f"[MISSING] {pid} not found in DB")
            continue

        header, seq = rec
        # IMPORTANT: keep protein_id as the exact ID your pipeline expects
        run_one_protein.delay(pid, seq)
        submitted += 1

        if submitted % 100 == 0:
            print(f"Submitted {submitted} tasks...")

    print(f"Done! Submitted {submitted} protein tasks. Missing in DB: {missing}")
