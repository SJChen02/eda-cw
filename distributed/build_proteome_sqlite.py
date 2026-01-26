#!/usr/bin/env python3
import gzip
import sqlite3
from pathlib import Path
import sys
import time

def parse_fasta_gz(path: Path):
    """
    Yields (protein_id, header, sequence).
    protein_id is taken as the first token after '>'.
    """
    header = None
    seq_chunks = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    pid = header[1:].split()[0]
                    yield pid, header[1:], "".join(seq_chunks)
                header = line
                seq_chunks = []
            else:
                seq_chunks.append(line)
        if header is not None:
            pid = header[1:].split()[0]
            yield pid, header[1:], "".join(seq_chunks)

def main():
    if len(sys.argv) != 3:
        print("Usage: build_proteome_sqlite.py <input.fasta.gz> <output.db>", file=sys.stderr)
        sys.exit(1)

    fasta_gz = Path(sys.argv[1])
    db_path = Path(sys.argv[2])

    if not fasta_gz.exists():
        print(f"ERROR: FASTA not found: {fasta_gz}", file=sys.stderr)
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_proteins_id ON proteins(id)")

    # Load data
    t0 = time.time()
    n = 0
    batch = []

    for pid, header, seq in parse_fasta_gz(fasta_gz):
        batch.append((pid, header, seq))
        if len(batch) >= 2000:
            cur.executemany("INSERT OR REPLACE INTO proteins(id, header, sequence) VALUES (?,?,?)", batch)
            con.commit()
            n += len(batch)
            print(f"Inserted {n} records...")
            batch = []

    if batch:
        cur.executemany("INSERT OR REPLACE INTO proteins(id, header, sequence) VALUES (?,?,?)", batch)
        con.commit()
        n += len(batch)

    cur.execute("SELECT COUNT(*) FROM proteins")
    total = cur.fetchone()[0]

    con.close()
    dt = time.time() - t0
    print(f"DONE. Inserted={n}, total_in_db={total}, time={dt:.1f}s")
    print(f"DB: {db_path}")

if __name__ == "__main__":
    main()
