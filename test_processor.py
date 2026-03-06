import pytest
from unittest.mock import MagicMock, call
import subprocess
import processor

def test_extract_audio_success(monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr('processor.subprocess.run', mock_run)
    
    result = processor.extract_audio('test.mp4', 'test.wav')
    
    assert result is True
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == 'ffmpeg'
    assert '-i' in args
    assert 'test.mp4' in args
    assert 'test.wav' in args

def test_extract_audio_failure(monkeypatch):
    mock_run = MagicMock(side_effect=subprocess.CalledProcessError(1, 'ffmpeg'))
    monkeypatch.setattr('processor.subprocess.run', mock_run)
    
    result = processor.extract_audio('test.mp4', 'test.wav')
    
    assert result is False

def test_pipeline_empty_queue(monkeypatch, capsys):
    mock_whisper = MagicMock()
    monkeypatch.setattr('processor.WhisperModel', mock_whisper)
    
    mock_connect = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_connect.return_value.cursor.return_value = mock_cursor
    monkeypatch.setattr('processor.sqlite3.connect', mock_connect)
    
    processor.run_processing_pipeline()
    
    captured = capsys.readouterr()
    assert "Queue is empty" in captured.out

def test_pipeline_missing_file(monkeypatch, capsys):
    mock_whisper = MagicMock()
    monkeypatch.setattr('processor.WhisperModel', mock_whisper)
    
    mock_connect = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("vid_miss", "vid_miss.mp4")]
    mock_connect.return_value.cursor.return_value = mock_cursor
    monkeypatch.setattr('processor.sqlite3.connect', mock_connect)
    
    mock_exists = MagicMock(return_value=False)
    monkeypatch.setattr('processor.os.path.exists', mock_exists)
    
    processor.run_processing_pipeline()
    
    captured = capsys.readouterr()
    assert "File missing for vid_miss" in captured.out

def test_pipeline_success(monkeypatch):
    mock_whisper_class = MagicMock()
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "Mocked transcription."
    mock_model.transcribe.return_value = ([mock_segment], {"language": "en"})
    mock_whisper_class.return_value = mock_model
    monkeypatch.setattr('processor.WhisperModel', mock_whisper_class)
    
    mock_connect = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("vid1", "vid1.mp4")]
    mock_connect.return_value.cursor.return_value = mock_cursor
    monkeypatch.setattr('processor.sqlite3.connect', mock_connect)
    
    mock_exists = MagicMock(return_value=True)
    monkeypatch.setattr('processor.os.path.exists', mock_exists)
    
    mock_extract = MagicMock(return_value=True)
    monkeypatch.setattr('processor.extract_audio', mock_extract)
    
    mock_remove = MagicMock()
    monkeypatch.setattr('processor.os.remove', mock_remove)
    
    processor.run_processing_pipeline()
    
    # Assert extract was called correctly
    mock_extract.assert_called_once_with("vid1.mp4", "vid1.wav")
    
    # Assert model ran on wav
    mock_model.transcribe.assert_called_once_with("vid1.wav", beam_size=5)
    
    # Assert SQL update happened
    mock_cursor.execute.assert_any_call(
        "UPDATE videos SET transcript = ? WHERE video_id = ?", 
        ("Mocked transcription.", "vid1")
    )
    mock_connect.return_value.commit.assert_called_once()
    
    # Assert Disk Cleanup deleted both MP4 and WAV
    assert mock_remove.call_count == 2
    mock_remove.assert_has_calls([call("vid1.mp4"), call("vid1.wav")])
