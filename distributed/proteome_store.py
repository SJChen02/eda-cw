import sqlite3
from pathlib import Path
from typing import Optional, Tuple, Iterable

DB_PATH = Path("/data/proteome.db")

def get_sequence(protein_id: str, db_path: Path = DB_PATH) -> Optional[str]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT sequence FROM proteins WHERE id = ?", (protein_id,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else None

def get_record(protein_id: str, db_path: Path = DB_PATH) -> Optional[Tuple[str, str]]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT header, sequence FROM proteins WHERE id = ?", (protein_id,))
    row = cur.fetchone()
    con.close()
    return (row[0], row[1]) if row else None
