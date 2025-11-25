"""
One-touch runner for the scraping workflow:
- remove_duplicates: drop codes already present in Update_Code.txt
- new_sc: scrape new codes, fetch chobit, download images, ingest DB
- update_sc: refresh existing codes and ingest DB

Usage:
    python scripts/run_bot.py
"""

import sys
from pathlib import Path

# Ensure project root and scripts/ are on sys.path so imports work no matter where we run from
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS_DIR = ROOT / "scripts"
for p in (SRC, ROOT, SCRIPTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from remove_duplicates import main as dedup_main
from new_sc import main as new_main
from update_sc import main as update_main


def main():
    print("Step 1/3: Removing duplicates from New_Code.txt vs Update_Code.txt...")
    dedup_main()

    print("Step 2/3: Scraping NEW codes (Chobit, images, JSON, DB)...")
    new_main()

    print("Step 3/3: Updating existing codes (JSON, DB)...")
    update_main()

    print("All steps completed.")


if __name__ == "__main__":
    main()
