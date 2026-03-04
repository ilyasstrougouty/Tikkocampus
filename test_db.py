import sqlite3
import pytest
import os
import db

@pytest.fixture
def temp_db_path(tmp_path):
    """Fixture that returns a path to a temporary SQLite database file."""
    return str(tmp_path / "test_tiktok_data.db")

@pytest.fixture
def patch_db_connection(monkeypatch, temp_db_path):
    """Patches db.get_connection to return a connection to the temp database."""
    def mock_get_connection():
        return sqlite3.connect(temp_db_path)
    
    monkeypatch.setattr('db.get_connection', mock_get_connection)
    return temp_db_path

def test_init_db(patch_db_connection):
    """Test that the database initializes correctly with the required table."""
    db_path = patch_db_connection
    db.init_db()
    
    # Check if 'videos' table exists
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
    table = cursor.fetchone()
    conn.close()

    assert table is not None
    assert table[0] == 'videos'

def test_insert_video_metadata(patch_db_connection):
    """Test inserting metadata into the database."""
    db_path = patch_db_connection
    db.init_db()

    video_data = {
        "video_id": "12345",
        "upload_date": "20231001",
        "caption": "Test video",
        "creator_name": "test_creator",
        "file_path": "temp_processing/12345.mp4"
    }

    db.insert_video_metadata(**video_data)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos WHERE video_id='12345'")
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == "12345"
    assert row[1] == "20231001"
    assert row[2] == "Test video"
    assert row[3] == "test_creator"
    assert row[4] == "temp_processing/12345.mp4"

def test_upsert_video_metadata(patch_db_connection):
    """Test that inserting identical video_id updates the existing record (upsert)."""
    db_path = patch_db_connection
    db.init_db()

    db.insert_video_metadata("123", "20230101", "old caption", "user", "path1")
    # Same ID, new caption
    db.insert_video_metadata("123", "20230101", "new caption", "user", "path2")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT caption, file_path FROM videos WHERE video_id='123'")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "new caption"
    assert row[1] == "path2"
