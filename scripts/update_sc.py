import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (SRC, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dlsite_app.services.scraper import save_work_to_json
from dlsite_app.services.ingest import ingest_json_files


UPDATE_FILE = ROOT / "codes" / "Update_Code.txt"


def load_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip().startswith("RJ")]


def main():
    codes = load_codes(UPDATE_FILE)
    if not codes:
        print("No codes in Update_Code.txt")
        return

    for code in codes:
        save_work_to_json(code, download_media=False)

    ingest_json_files()
    print(f"Updated {len(codes)} code(s).")


if __name__ == "__main__":
    main()
