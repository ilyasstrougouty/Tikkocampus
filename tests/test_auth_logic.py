import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
import cookie_manager

class TestAuthLogic(unittest.TestCase):
    
    @patch('auth.sync_playwright')
    @patch('auth._launch_best_browser')
    @patch('auth.os._exit')
    @patch('cookie_manager.write_netscape')
    def test_run_login_flow_success(self, mock_write_netscape, mock_exit, mock_launch_browser, mock_sync_playwright):
        # Setup mocks
        mock_playwright_context = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright_context
        
        mock_browser = MagicMock()
        mock_launch_browser.return_value = mock_browser
        mock_browser.is_connected.return_value = True
        
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_context.pages = [mock_page]
        
        # Simulate the cookie polling
        # First call: no sessionid
        # Second call: sessionid appears
        mock_context.cookies.side_effect = [
            [{"name": "other_cookie", "value": "123"}],
            [{"name": "sessionid", "value": "test_session_id_xyz"}, {"name": "tt_webid_v2", "value": "123"}],
            [{"name": "sessionid", "value": "test_session_id_xyz"}, {"name": "tt_webid_v2", "value": "123"}] # final_cookies
        ]
        
        # To avoid actual time.sleep blocking the test
        with patch('time.sleep', return_value=None):
            auth.run_login_flow()
            
        # Assertions
        mock_launch_browser.assert_called_once()
        mock_context.new_page.assert_called_once()
        mock_page.goto.assert_called_with("https://www.tiktok.com/login", timeout=60000)
        
        # Verify that write_netscape was called with the final cookies
        mock_write_netscape.assert_called_once()
        args, kwargs = mock_write_netscape.call_args
        self.assertEqual(len(args[0]), 2)
        self.assertEqual(args[0][0]["name"], "sessionid")
        self.assertEqual(kwargs.get("source"), "playwright-auth")
        
        # Verify browser closed and exited gracefully
        mock_browser.close.assert_called_once()
        mock_exit.assert_called_with(0)

if __name__ == '__main__':
    unittest.main()
