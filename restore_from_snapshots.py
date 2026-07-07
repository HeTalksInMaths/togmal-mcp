#!/usr/bin/env python3
"""
Restore From Snapshots
======================

Restores the full ToGMAL data layer on a fresh machine from the committed
snapshots (no scraping, no network):

    python3 restore_from_snapshots.py           # restore data/*.json
    python3 restore_from_snapshots.py --rebuild # + datastore & semantic index

Restores:
    data/unified_database_complete.json   (13K questions, enrichments baked in)
    data/error_taxonomy.json
    data/cot_failure_analysis.json
    data/comprehensive_error_patterns.json
    data/expanded_taxonomy.json
    data/semantic_evaluation_results.json
    data/combined_tier_evaluation.json

With --rebuild, also regenerates the derived artifacts (~2 min):
    mcp_datastore/            (python3 build_mcp_datastore.py)
    data/semantic_index.pkl   (python3 semantic_difficulty_checker.py build)
"""

import gzip
import shutil
import subprocess
import sys
from pathlib import Path

SNAPSHOTS = Path("./snapshots")
DATA = Path("./data")


def main():
    DATA.mkdir(exist_ok=True)

    archives = sorted(SNAPSHOTS.glob("*.json.gz"))
    if not archives:
        sys.exit(f"No snapshots found in {SNAPSHOTS}/")

    for src in archives:
        dest = DATA / src.name[:-3]  # strip .gz
        with gzip.open(src, 'rb') as f_in, open(dest, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        print(f"✅ {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")

    if '--rebuild' in sys.argv:
        print("\nRebuilding derived artifacts...")
        subprocess.run([sys.executable, "build_mcp_datastore.py"], check=True)
        subprocess.run([sys.executable, "semantic_difficulty_checker.py", "build"],
                       check=True)

    print("\n✅ Restore complete.")
    if '--rebuild' not in sys.argv:
        print("Run with --rebuild to also regenerate mcp_datastore/ and the "
              "semantic index, or run those builders yourself when needed.")


if __name__ == '__main__':
    main()
