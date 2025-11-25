import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (SRC, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dlsite_app.config import settings
from dlsite_app.services.scraper import save_work_to_json
from dlsite_app.services.ingest import ingest_json_files


CODE_DIR = ROOT / "codes"
NEW_FILE = CODE_DIR / "New_Code.txt"
UPDATE_FILE = CODE_DIR / "Update_Code.txt"
IMAGE_ROOT = settings.image_root


def load_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip().startswith("RJ")]


def write_codes(path: Path, codes: list[str]):
    uniq = sorted(set(codes))
    path.write_text("\n".join(uniq) + ("\n" if uniq else ""), encoding="utf-8")


def main():
    new_codes = load_codes(NEW_FILE)
    if not new_codes:
        print("No codes in New_Code.txt")
        return

    update_codes = set(load_codes(UPDATE_FILE))
    processed = []

    for code in new_codes:
        # Skip if already processed
        if code in processed or code in update_codes:
            continue
        success = save_work_to_json(code, download_media=True, image_root=IMAGE_ROOT)
        if success:
            processed.append(code)

    # Remove processed codes from New_Code.txt
    remaining = [c for c in new_codes if c not in processed]
    write_codes(NEW_FILE, remaining)

    # Add processed to Update_Code.txt
    updated_list = sorted(update_codes | set(processed))
    write_codes(UPDATE_FILE, updated_list)

    # Update DB with new/updated JSON
    if processed:
        ingest_json_files()
    print(f"Processed {len(processed)} code(s).")


if __name__ == "__main__":
    main()
