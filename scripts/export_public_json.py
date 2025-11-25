import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (SRC, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dlsite_app.db import get_db_connection
from dlsite_app.config import settings


def export_public_json(dest: Path | None = None):
    """Dump works+stats into a static JSON for deployment without DB."""
    output_path = Path(dest or (ROOT / "static" / "works.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            w.rj_code, w.site_id, w.title, w.circle, w.release_date, w.description,
            w.img_url, w.media, w.embeds, w.chobit_url, w.genres, w.cv, w.content_tokens,
            s.dl_count, s.price, s.rate_average, s.wishlist_count, s.rate_count_detail
        FROM works w
        LEFT JOIN stats s ON w.rj_code = s.rj_code
        """
    )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        work = dict(row)

        def safe_json_load(val):
            if not val:
                return []
            try:
                return json.loads(val)
            except Exception:
                return []

        work["genres"] = safe_json_load(work.get("genres"))
        work["cv"] = safe_json_load(work.get("cv"))
        work["media"] = safe_json_load(work.get("media"))
        work["embeds"] = safe_json_load(work.get("embeds"))
        work["rate_count_detail"] = safe_json_load(work.get("rate_count_detail"))
        work["content_tokens"] = safe_json_load(work.get("content_tokens"))

        # prepend cv count as tag if available (mirrors API behavior)
        if work["cv"]:
            work["genres"] = [f"{len(work['cv'])}cv"] + work["genres"]

        result.append(work)

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(result)} works to {output_path}")


if __name__ == "__main__":
    export_public_json()
