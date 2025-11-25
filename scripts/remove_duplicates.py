from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = ROOT / "codes"
NEW_FILE = CODE_DIR / "New_Code.txt"
UPDATE_FILE = CODE_DIR / "Update_Code.txt"


def load_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip().startswith("RJ")]


def write_codes(path: Path, codes: list[str]) -> None:
    uniq = sorted(set(codes))
    path.write_text("\n".join(uniq) + ("\n" if uniq else ""), encoding="utf-8")


def main():
    new_codes = load_codes(NEW_FILE)
    update_codes = set(load_codes(UPDATE_FILE))

    filtered = [code for code in new_codes if code not in update_codes]
    removed = len(new_codes) - len(filtered)

    write_codes(NEW_FILE, filtered)
    print(f"Removed {removed} duplicate code(s) already present in Update_Code.txt.")


if __name__ == "__main__":
    main()
