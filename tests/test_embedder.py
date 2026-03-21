import pytest
from unittest.mock import MagicMock, call
import embedder

def test_pipeline_empty_queue(monkeypatch, capsys):
    # Mock ChromaDB singleton client
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    monkeypatch.setattr('embedder.get_chroma_client', MagicMock(return_value=mock_client))
    
    # Mock TextSplitter
    mock_splitter = MagicMock()
    monkeypatch.setattr('embedder.RecursiveCharacterTextSplitter', mock_splitter)
    
    # Mock SQLite with an empty queue
    mock_connect = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_connect.return_value.cursor.return_value = mock_cursor
    
    # Mock the db_session context manager
    mock_session = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_connect.return_value
    monkeypatch.setattr('embedder.db_session', mock_session)
    
    embedder.run_embedding_pipeline()
    
    captured = capsys.readouterr()
    assert "Queue is empty" in captured.out
    mock_collection.add.assert_not_called()

def test_pipeline_add_column_exception(monkeypatch, capsys):
    # Setup chroma mock
    mock_chroma = MagicMock()
    monkeypatch.setattr('embedder.chromadb', mock_chroma)
    
    mock_splitter = MagicMock()
    monkeypatch.setattr('embedder.RecursiveCharacterTextSplitter', mock_splitter)
    
    # Mock SQLite with an OperationalError when altering table
    import sqlite3
    mock_connect = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    
    def side_effect_execute(query, *args):
        if "ALTER TABLE" in query:
            raise sqlite3.OperationalError("Column already exists")
    
    mock_cursor.execute.side_effect = side_effect_execute
    mock_connect.return_value.cursor.return_value = mock_cursor
    
    # Mock the db_session context manager
    mock_session = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_connect.return_value
    monkeypatch.setattr('embedder.db_session', mock_session)
    
    embedder.run_embedding_pipeline()
    
    captured = capsys.readouterr()
    assert "Queue is empty" in captured.out

def test_pipeline_success(monkeypatch, capsys):
    # Setup chroma mock
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    monkeypatch.setattr('embedder.get_chroma_client', MagicMock(return_value=mock_client))
    
    # Mock text splitter to return two chunks
    mock_splitter_class = MagicMock()
    mock_splitter_instance = MagicMock()
    mock_splitter_instance.split_text.return_value = ["chunk 1", "chunk 2"]
    mock_splitter_class.return_value = mock_splitter_instance
    monkeypatch.setattr('embedder.RecursiveCharacterTextSplitter', mock_splitter_class)
    
    # Mock SQLite with a single video ready for vectorization
    mock_connect = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("vid123", "Full transcript text here", "file1.mp4", "test_creator")]
    mock_connect.return_value.cursor.return_value = mock_cursor
    
    # Mock the db_session context manager
    mock_session = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_connect.return_value
    monkeypatch.setattr('embedder.db_session', mock_session)
    
    # Run the pipeline
    embedder.run_embedding_pipeline()
    
    # Assert ChromaDB injection
    mock_collection.add.assert_called_once_with(
        documents=["chunk 1", "chunk 2"],
        metadatas=[
            {"video_id": "vid123", "creator": "test_creator", "original_url": "https://www.tiktok.com/@test_creator/video/vid123", "chunk_index": 0},
            {"video_id": "vid123", "creator": "test_creator", "original_url": "https://www.tiktok.com/@test_creator/video/vid123", "chunk_index": 1}
        ],
        ids=["vid123_chunk_0", "vid123_chunk_1"]
    )
    
    # Assert database update
    # Assert database update
    mock_cursor.execute.assert_any_call("UPDATE videos SET is_vectorized = 1 WHERE video_id = ?", ("vid123",))
    mock_connect.return_value.commit.assert_called()
    
    captured = capsys.readouterr()
    assert "[SUCCESS] 2 chunks embedded for vid123" in captured.out
    assert "Phase 3 pipeline complete" in captured.out
