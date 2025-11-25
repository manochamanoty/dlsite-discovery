import json
from datetime import datetime
from pathlib import Path

from dlsite_app.config import settings
from dlsite_app.db import get_db_connection


def ingest_json_files(data_dir: str | Path | None = None):
    data_dir = Path(data_dir or settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    json_files = sorted(data_dir.glob("RJ*.json"))
    print(f"Found {len(json_files)} JSON files in {data_dir}.")

    for filepath in json_files:
        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)

            rj_code = data.get("rj_code")
            static = data.get("static_info", {}) or {}
            dynamic = data.get("dynamic_info", {}) or {}

            if not rj_code:
                continue

            print(f"Ingesting {rj_code}...")

            cursor.execute(
                """
                INSERT OR REPLACE INTO works (
                    rj_code, site_id, title, circle, release_date, description,
                    img_url, media, embeds, chobit_url, genres, cv, content_tokens, file_size, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rj_code,
                    dynamic.get("site_id", "maniax"),
                    static.get("title"),
                    static.get("circle"),
                    static.get("release_date"),
                    static.get("description"),
                    dynamic.get("work_image") if dynamic else None,
                    json.dumps(static.get("media", []), ensure_ascii=False),
                    json.dumps(static.get("embeds", []), ensure_ascii=False),
                    static.get("chobit_url"),
                    json.dumps(static.get("genres", []), ensure_ascii=False),
                    json.dumps(static.get("cv", []), ensure_ascii=False),
                    json.dumps(static.get("content_tokens", []), ensure_ascii=False),
                    static.get("file_size"),
                    datetime.now(),
                ),
            )

            if dynamic:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO stats (
                        rj_code, dl_count, wishlist_count, price,
                        rate_average, rate_count_detail, affiliate_deny, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rj_code,
                        dynamic.get("dl_count", 0),
                        dynamic.get("wishlist_count", 0),
                        dynamic.get("price", 0),
                        dynamic.get("rate_average_2dp", 0.0),
                        json.dumps(dynamic.get("rate_count_detail", []), ensure_ascii=False),
                        dynamic.get("affiliate_deny", 0),
                        datetime.now(),
                    ),
                )

        except Exception as exc:
            print(f"Error processing {filepath}: {exc}")

    conn.commit()
    conn.close()
    print("Ingestion complete.")
