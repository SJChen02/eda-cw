#!/usr/bin/env python3
import gzip
import sqlite3
from pathlib import Path
import sys
import time


def open_maybe_gz(path: Path):
    """
    Open plain FASTA or gzipped FASTA transparently.
    """
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def parse_fasta(path: Path):
    """
    Yields (protein_id, header, sequence).
    protein_id is taken as the first token after '>'.
    Works for .fasta and .fasta.gz
    """
    header = None
    seq_chunks = []

    with open_maybe_gz(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith(">"):
                if header is not None:
                    pid = header.split()[0]
                    yield pid, header, "".join(seq_chunks)

                header = line[1:]   # drop leading '>'
                seq_chunks = []
            else:
                seq_chunks.append(line)

        if header is not None:
            pid = header.split()[0]
            yield pid, header, "".join(seq_chunks)


def main():
    if len(sys.argv) != 3:
        print("Usage: build_proteome_sqlite.py <input.fasta(.gz)> <output.db>", file=sys.stderr)
        sys.exit(1)

    fasta_path = Path(sys.argv[1])
    db_path = Path(sys.argv[2])

    if not fasta_path.exists():
        print(f"ERROR: FASTA not found: {fasta_path}", file=sys.stderr)
        sys.exit(1)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create DB
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS proteins (
            id TEXT PRIMARY KEY,
            header TEXT NOT NULL,
            sequence TEXT NOT NULL
        )
    """)

    t0 = time.time()
    n = 0
    batch = []

    for pid, header, seq in parse_fasta(fasta_path):
        batch.append((pid, header, seq))
        if len(batch) >= 2000:
            cur.executemany(
                "INSERT OR REPLACE INTO proteins(id, header, sequence) VALUES (?,?,?)",
                batch
            )
            con.commit()
            n += len(batch)
            print(f"Inserted {n} records...")
            batch = []

    if batch:
        cur.executemany(
            "INSERT OR REPLACE INTO proteins(id, header, sequence) VALUES (?,?,?)",
            batch
        )
        con.commit()
        n += len(batch)

    total = cur.execute("SELECT COUNT(*) FROM proteins").fetchone()[0]
    con.close()

    dt = time.time() - t0
    print(f"DONE. Inserted={n}, total_in_db={total}, time={dt:.1f}s")
    print(f"DB: {db_path}")


if __name__ == "__main__":
    main()