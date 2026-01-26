#!/usr/bin/env python3
import sys
from proteome_store import get_record

def main():
    if len(sys.argv) != 2:
        print("Usage: lookup_protein.py <PROTEIN_ID>", file=sys.stderr)
        sys.exit(1)

    pid = sys.argv[1].strip()
    rec = get_record(pid)
    if not rec:
        print(f"NOT FOUND: {pid}", file=sys.stderr)
        sys.exit(2)

    header, seq = rec
    print(f">{header}")
    print(seq)

if __name__ == "__main__":
    main()
