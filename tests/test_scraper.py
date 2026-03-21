import pytest
from unittest.mock import MagicMock
import scraper
import config

def test_download_profile_videos_success(monkeypatch, capsys):
    """Test scraping logic when Playwright extracts info successfully."""
    mock_insert = MagicMock()
    monkeypatch.setattr('scraper.insert_video_metadata', mock_insert)

    mock_download = MagicMock(return_value=f'{config.TEMP_PROCESSING_DIR}/video_1.mp4')
    monkeypatch.setattr('scraper.download_video_file', mock_download)

    # Mock db_session
    mock_session = MagicMock()
    mock_session.return_value.__enter__.return_value = MagicMock()
    monkeypatch.setattr('scraper.db_session', mock_session)

    # Mock the playwright context manager
    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser
    
    mock_sync_pw = MagicMock()
    mock_sync_pw.__enter__.return_value = mock_pw
    
    # We need to simulate the handle_response callback being triggered
    # The scraper uses `page.on("response", handle_response)`
    # We'll intercept that registration and manually call the callback
    def mock_on(event, callback):
        if event == "response":
            # Simulate a fake API response matching TikTok's structure
            mock_response = MagicMock()
            mock_response.url = "https://example.com/api/item_list"
            mock_response.json.return_value = {
                'itemList': [
                    {
                        'id': 'video_1',
                        'createTime': 1701388800, # 2023-12-01
                        'desc': 'Test Description 1',
                        'author': {'uniqueId': 'test_creator_1'},
                        'video': {'playAddr': 'http://example.com/vid1.mp4'}
                    }
                ]
            }
            callback(mock_response)
            
    mock_page.on = mock_on

    monkeypatch.setattr('scraper.sync_playwright', MagicMock(return_value=mock_sync_pw))

    profile_url = "https://www.tiktok.com/@testuser"
    scraper.download_profile_videos(profile_url, max_downloads=1)

    assert mock_download.call_count == 1
    assert mock_insert.call_count == 1
    
    mock_insert.assert_any_call(
        video_id='video_1',
        upload_date='20231201',
        caption='Test Description 1',
        creator_name='test_creator_1',
        file_path=f'{config.TEMP_PROCESSING_DIR}/video_1.mp4'
    )

    captured = capsys.readouterr()
    assert "Successfully processed profile" in captured.out

def test_download_profile_videos_failure(monkeypatch, capsys):
    """Test handled exception when Playwright fails."""
    mock_insert = MagicMock()
    monkeypatch.setattr('scraper.insert_video_metadata', mock_insert)

    # Mock sync_playwright to raise an error
    mock_sync_pw = MagicMock()
    mock_sync_pw.__enter__.side_effect = Exception("Mocked playwright error")
    monkeypatch.setattr('scraper.sync_playwright', mock_sync_pw)
    
    # Mock db_session
    mock_session = MagicMock()
    mock_session.return_value.__enter__.return_value = MagicMock()
    monkeypatch.setattr('scraper.db_session', mock_session)

    scraper.download_profile_videos("https://www.tiktok.com/@baduser")

    assert mock_insert.call_count == 0
