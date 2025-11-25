from dlsite_app.db import get_db_connection


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS works")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS works (
            rj_code TEXT PRIMARY KEY,
            site_id TEXT,
            title TEXT,
            circle TEXT,
            release_date TEXT,
        description TEXT,
        img_url TEXT,
        media TEXT,
        embeds TEXT,
        chobit_url TEXT,
        genres TEXT,
        cv TEXT,
        content_tokens TEXT,
        file_size TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stats (
            rj_code TEXT PRIMARY KEY,
            dl_count INTEGER,
            wishlist_count INTEGER,
            price INTEGER,
            rate_average REAL,
            rate_count_detail TEXT,
            affiliate_deny INTEGER,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rj_code) REFERENCES works (rj_code)
        )
        """
    )

    conn.commit()
    conn.close()
    print("Database initialized successfully.")
