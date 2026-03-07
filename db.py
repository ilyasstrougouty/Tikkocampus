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
    conn.commit()
    conn.close()

def reset_database():
    """Wipes all video records so a fresh scrape starts clean."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM videos')
    conn.commit()
    conn.close()

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
