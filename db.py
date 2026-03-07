import sqlite3
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the SQLite database with the required schema."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            upload_date TEXT,
            caption TEXT,
            creator_name TEXT,
            file_path TEXT,
            transcript TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scrape_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_url TEXT NOT NULL,
            creator_name TEXT,
            video_count INTEGER,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def reset_database():
    """Wipes all video records so a fresh scrape starts clean."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM videos')
    conn.commit()
    conn.close()

def save_scrape_history(profile_url, creator_name, video_count):
    """Saves a completed scrape to the history table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO scrape_history (profile_url, creator_name, video_count)
        VALUES (?, ?, ?)
    ''', (profile_url, creator_name, video_count))
    conn.commit()
    conn.close()

def get_scrape_history(limit=20):
    """Returns the most recent scrape history entries."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT profile_url, creator_name, video_count, scraped_at 
        FROM scrape_history ORDER BY scraped_at DESC LIMIT ?
    ''', (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def insert_video_metadata(video_id, upload_date, caption, creator_name, file_path):
    """Inserts or updates a video record in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO videos (video_id, upload_date, caption, creator_name, file_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (video_id, upload_date, caption, creator_name, file_path))
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)

