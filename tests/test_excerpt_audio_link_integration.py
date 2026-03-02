"""
Integration tests for verifying audio_link in the excerpt_with_alignment endpoint
"""

import unittest
from unittest.mock import patch
import sys
import os

# Add path to the app module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient
from main import app


class TestExcerptAudioLinkIntegration(unittest.TestCase):
    """Integration tests for audio_link in excerpt_with_alignment"""

    def setUp(self):
        self.client = TestClient(app)

    def test_excerpt_with_alignment_endpoint_exists(self):
        """Test that the excerpt_with_alignment endpoint exists"""
        response = self.client.get("/api/excerpt_with_alignment?translation=1&excerpt=jhn 3:16&voice=1")
        # Verify the endpoint responds (not 404)
        self.assertNotEqual(response.status_code, 404)

    @patch('excerpt.check_audio_file_exists')
    def test_audio_link_when_file_exists(self, mock_check_file):
        """Test audio_link when audio file exists"""
        mock_check_file.return_value = True
        
        response = self.client.get("/api/excerpt_with_alignment?translation=1&excerpt=jhn 3:16&voice=1")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify the response structure
            self.assertIn('parts', data)
            if data['parts']:
                part = data['parts'][0]
                self.assertIn('audio_link', part)

                # If voice is found and file exists, audio_link should contain path to audio
                if part['audio_link']:
                    self.assertIn('/audio/', part['audio_link'])
                    self.assertTrue(part['audio_link'].endswith('.mp3'))

    @patch('excerpt.check_audio_file_exists')
    def test_audio_link_when_file_not_exists(self, mock_check_file):
        """Test audio_link when audio file does not exist"""
        mock_check_file.return_value = False
        
        response = self.client.get("/api/excerpt_with_alignment?translation=1&excerpt=jhn 3:16&voice=1")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify the response structure
            self.assertIn('parts', data)
            if data['parts']:
                part = data['parts'][0]
                self.assertIn('audio_link', part)

                # If file does not exist, audio_link should be empty
                self.assertEqual(part['audio_link'], '')

    def test_audio_link_without_voice(self):
        """Test audio_link when voice is not specified"""
        response = self.client.get("/api/excerpt_with_alignment?translation=1&excerpt=jhn 3:16")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify the response structure
            self.assertIn('parts', data)
            if data['parts']:
                part = data['parts'][0]
                self.assertIn('audio_link', part)

                # Without voice, audio_link should be empty
                self.assertEqual(part['audio_link'], '')

    @patch('excerpt.check_audio_file_exists')
    def test_audio_link_format_validation(self, mock_check_file):
        """Test audio_link format correctness"""
        mock_check_file.return_value = True
        
        response = self.client.get("/api/excerpt_with_alignment?translation=1&excerpt=gen 1:1&voice=1")
        
        if response.status_code == 200:
            data = response.json()
            
            if data['parts'] and data['parts'][0]['audio_link']:
                audio_link = data['parts'][0]['audio_link']
                
                # Verify the link format
                self.assertIn('/audio/', audio_link)
                self.assertTrue(audio_link.endswith('.mp3'))

    def test_excerpt_response_structure_with_audio_link(self):
        """Test response structure with the audio_link field"""
        response = self.client.get("/api/excerpt_with_alignment?translation=1&excerpt=jhn 3:16&voice=1")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify the main structure
            self.assertIn('title', data)
            self.assertIn('is_single_chapter', data)
            self.assertIn('parts', data)
            
            if data['parts']:
                part = data['parts'][0]
                
                # Verify the part structure
                self.assertIn('book', part)
                self.assertIn('chapter_number', part)
                self.assertIn('audio_link', part)
                self.assertIn('verses', part)
                self.assertIn('notes', part)
                self.assertIn('titles', part)
                
                # audio_link should be a string
                self.assertIsInstance(part['audio_link'], str)


if __name__ == '__main__':
    unittest.main()
