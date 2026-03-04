import pytest
from unittest.mock import MagicMock
import scraper
import config

def test_download_profile_videos_success(monkeypatch, capsys):
    """Test scraping logic when yt-dlp extracts info successfully."""
    # Mock insert_video_metadata so it doesn't touch the real DB
    mock_insert = MagicMock()
    monkeypatch.setattr('scraper.insert_video_metadata', mock_insert)

    mock_exists = MagicMock(return_value=True)
    monkeypatch.setattr('scraper.os.path.exists', mock_exists)

    # Mock YoutubeDL context manager and its extract_info method
    mock_ydl = MagicMock()
    mock_ydl.__enter__.return_value = mock_ydl
    mock_ydl.extract_info.return_value = {
        'entries': [
            {
                'id': 'video_1',
                'upload_date': '20231201',
                'title': 'Test Title 1',
                'description': 'Test Description 1',
                'uploader': 'test_creator_1',
                'ext': 'mp4'
            },
            {
                'id': 'video_2',
                'upload_date': '20231202',
                'title': '', # Title missing, should use description
                'description': 'Test Description 2',
                'channel': 'test_creator_2', # uploader missing, uses channel
                'ext': 'mkv'
            }
        ]
    }

    mock_YoutubeDL = MagicMock(return_value=mock_ydl)
    monkeypatch.setattr('scraper.yt_dlp.YoutubeDL', mock_YoutubeDL)

    # Run the function
    profile_url = "https://www.tiktok.com/@testuser"
    scraper.download_profile_videos(profile_url, max_downloads=2)

    # Asserts
    assert mock_ydl.extract_info.called
    assert mock_ydl.extract_info.call_args[0][0] == profile_url
    assert mock_ydl.extract_info.call_args[1]['download'] is True

    assert mock_insert.call_count == 2
    
    # Check the first call parameters
    mock_insert.assert_any_call(
        video_id='video_1',
        upload_date='20231201',
        caption='Test Title 1',
        creator_name='test_creator_1',
        file_path=f'{config.TEMP_PROCESSING_DIR}/video_1.mp4'
    )

    # Check the second call parameters
    mock_insert.assert_any_call(
        video_id='video_2',
        upload_date='20231202',
        caption='Test Description 2',
        creator_name='test_creator_2',
        file_path=f'{config.TEMP_PROCESSING_DIR}/video_2.mkv'
    )

    captured = capsys.readouterr()
    assert "Successfully processed profile" in captured.out

def test_download_profile_videos_failure(monkeypatch, capsys):
    """Test handled exception when yt-dlp fails."""
    mock_insert = MagicMock()
    monkeypatch.setattr('scraper.insert_video_metadata', mock_insert)

    mock_ydl = MagicMock()
    mock_ydl.__enter__.return_value = mock_ydl
    mock_ydl.extract_info.side_effect = Exception("Mocked download error")
    
    mock_YoutubeDL = MagicMock(return_value=mock_ydl)
    monkeypatch.setattr('scraper.yt_dlp.YoutubeDL', mock_YoutubeDL)

    scraper.download_profile_videos("https://www.tiktok.com/@baduser")

    # DB insert should not be called
    assert mock_insert.call_count == 0

    # Output should contain the error
    captured = capsys.readouterr()
    assert "Error scraping" in captured.err
    assert "Mocked download error" in captured.err
