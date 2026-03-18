import sqlite3
from contextlib import contextmanager
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

@contextmanager
def db_session():
    """Context manager for handling database connections and ensuring they close."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initializes the SQLite database with the required schema."""
    with db_session() as conn:
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
                creator_nickname TEXT,
                video_count INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_name TEXT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # MIGRATION: Check if creator_nickname exists, if not add it
        try:
            cursor.execute("PRAGMA table_info(scrape_history)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'creator_nickname' not in columns:
                print("Migrating database: Adding creator_nickname to scrape_history...")
                cursor.execute("ALTER TABLE scrape_history ADD COLUMN creator_nickname TEXT")
                conn.commit()
                print("Migration successful.")
        except Exception as e:
            print(f"Migration error (non-fatal): {e}")

def reset_database():
    """Wipes all video records so a fresh scrape starts clean."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM videos')
        conn.commit()

def save_scrape_history(profile_url, creator_name, creator_nickname, video_count):
    """Saves a completed scrape to the history table."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scrape_history (profile_url, creator_name, creator_nickname, video_count)
            VALUES (?, ?, ?, ?)
        ''', (profile_url, creator_name, creator_nickname, video_count))
        conn.commit()

def delete_creator(creator_name):
    """Hard-deletes a creator, all their video metadata from SQLite, and physical files."""
    import os
    with db_session() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch file paths to delete physical files
        cursor.execute('SELECT file_path FROM videos WHERE creator_name = ?', (creator_name,))
        video_files = cursor.fetchall()
        
        for (file_path,) in video_files:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    # Also try to remove associated .wav if it exists (though pipeline usually cleans it)
                    wav_path = file_path.replace('.mp4', '.wav')
                    if os.path.exists(wav_path):
                        os.remove(wav_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
    
        # 2. Delete from SQLite
        cursor.execute('DELETE FROM scrape_history WHERE creator_name = ?', (creator_name,))
        cursor.execute('DELETE FROM videos WHERE creator_name = ?', (creator_name,))
        cursor.execute('DELETE FROM chat_messages WHERE creator_name = ?', (creator_name,))
        conn.commit()
    print(f"Successfully deleted creator {creator_name} and all associated files.")

def get_scrape_history(limit=20):
    """Returns the most recent scrape history entries."""
    with db_session() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT profile_url, creator_name, creator_nickname, video_count, scraped_at 
            FROM scrape_history ORDER BY scraped_at DESC LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

def insert_video_metadata(video_id, upload_date, caption, creator_name, file_path):
    """Inserts or updates a video record in the database."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO videos (video_id, upload_date, caption, creator_name, file_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (video_id, upload_date, caption, creator_name, file_path))
        conn.commit()

def save_chat_message(creator_name, role, content):
    """Saves a single chat message (user or ai) for a given creator."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_messages (creator_name, role, content)
            VALUES (?, ?, ?)
        ''', (creator_name, role, content))
        conn.commit()

def get_chat_history(creator_name):
    """Retrieves all chat messages for a given creator in chronological order."""
    with db_session() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, content, created_at
            FROM chat_messages 
            WHERE creator_name = ?
            ORDER BY created_at ASC
        ''', (creator_name,))
        return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)

