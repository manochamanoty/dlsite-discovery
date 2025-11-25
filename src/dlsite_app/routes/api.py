import json
from pathlib import Path
from flask import Blueprint, jsonify

from dlsite_app.config import settings
from dlsite_app.db import get_db_connection


api_bp = Blueprint("api", __name__)
STATIC_WORKS_PATH = settings.base_dir / "static" / "works.json"


def generate_affiliate_link(work: dict) -> str | None:
    rj_code = work.get("rj_code")
    if not rj_code:
        return None
    site_id = work.get("site_id", "maniax")
    return (
        f"https://dlaf.jp/{site_id}/dlaf/=/t/i/link/work/aid/{settings.affiliate_id}/id/{rj_code}.html"
    )


def load_static_works() -> list[dict]:
    """Fallback loader when DB is absent (e.g., Vercel static deploy)."""
    path = Path(STATIC_WORKS_PATH)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


@api_bp.route("/works")
def works():
    rows = []
    try:
        conn = get_db_connection()
        query = """
            SELECT 
                w.rj_code, w.site_id, w.title, w.circle, w.release_date, w.description, w.img_url, w.media, w.embeds, w.chobit_url, w.genres, w.cv, w.content_tokens,
                s.dl_count, s.price, s.rate_average, s.wishlist_count, s.rate_count_detail
            FROM works w
            LEFT JOIN stats s ON w.rj_code = s.rj_code
        """
        rows = conn.execute(query).fetchall()
    except Exception:
        rows = []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # If DB is unavailable or empty (e.g., Vercel), serve static snapshot
    if not rows:
        static_data = load_static_works()
        return jsonify(static_data)

    result = []
    for row in rows:
        work = dict(row)
        def safe_json_load(key):
            val = work.get(key)
            if not val:
                return []
            try:
                return json.loads(val)
            except Exception:
                return []

        work["genres"] = safe_json_load("genres")

        # CV cleanup
        if work.get("cv"):
            try:
                raw_cv = json.loads(work["cv"])
                clean_cv = [c for c in raw_cv if c and c.strip() and c != "/"]
                work["cv"] = clean_cv
                if clean_cv:
                    work["genres"].insert(0, f"{len(clean_cv)}cv")
            except Exception:
                work["cv"] = []
        else:
            work["cv"] = []

        work["media"] = safe_json_load("media")
        work["embeds"] = safe_json_load("embeds")
        work["rate_count_detail"] = safe_json_load("rate_count_detail")
        work["content_tokens"] = safe_json_load("content_tokens")

        work["affiliate_url"] = generate_affiliate_link(work)
        result.append(work)

    return jsonify(result)
