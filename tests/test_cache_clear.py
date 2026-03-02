import unittest
from fastapi.testclient import TestClient
from main import app
from excerpt import get_all_existing_audio_chapters, get_existing_audio_chapters, check_audio_file_exists


class TestCacheClear(unittest.TestCase):
    """Tests for verifying clearing of all caches"""

    def setUp(self):
        self.client = TestClient(app)
        # Get JWT token for authorization
        login_response = self.client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        self.assertEqual(login_response.status_code, 200)
        self.token = login_response.json()["access_token"]

    def test_cache_clear_clears_lru_caches(self):
        """Test that cache clear clears LRU caches from excerpt.py"""

        # Populate LRU caches by calling the functions
        get_all_existing_audio_chapters("syn", "bondarenko")
        get_existing_audio_chapters("syn", "bondarenko", 1)
        check_audio_file_exists("syn", "bondarenko", 1, 1)
        
        # Verify the caches are populated
        cache_info_before_all = get_all_existing_audio_chapters.cache_info()
        cache_info_before_existing = get_existing_audio_chapters.cache_info()
        cache_info_before_check = check_audio_file_exists.cache_info()
        
        self.assertGreater(cache_info_before_all.currsize, 0, "get_all_existing_audio_chapters cache should have items")
        self.assertGreater(cache_info_before_existing.currsize, 0, "get_existing_audio_chapters cache should have items")
        self.assertGreater(cache_info_before_check.currsize, 0, "check_audio_file_exists cache should have items")
        
        # Clear cache via API
        response = self.client.post(
            "/api/cache/clear",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify the response structure
        self.assertIn("message", data)
        self.assertIn("items_cleared", data)
        self.assertIn("lru_caches_cleared", data)
        self.assertEqual(len(data["lru_caches_cleared"]), 3)
        
        # Verify that LRU caches are cleared
        cache_info_after_all = get_all_existing_audio_chapters.cache_info()
        cache_info_after_existing = get_existing_audio_chapters.cache_info()
        cache_info_after_check = check_audio_file_exists.cache_info()
        
        self.assertEqual(cache_info_after_all.currsize, 0, "get_all_existing_audio_chapters cache should be empty")
        self.assertEqual(cache_info_after_existing.currsize, 0, "get_existing_audio_chapters cache should be empty")
        self.assertEqual(cache_info_after_check.currsize, 0, "check_audio_file_exists cache should be empty")

    def test_cache_clear_with_valid_token_succeeds(self):
        """Test that cache clear works with a valid JWT token"""

        # Clearing with a valid token should work
        response = self.client.post(
            "/api/cache/clear",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("lru_caches_cleared", data)


if __name__ == '__main__':
    unittest.main()
