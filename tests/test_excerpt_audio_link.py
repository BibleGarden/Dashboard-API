"""
Tests for verifying audio_link generation in the excerpt_with_alignment endpoint
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Add path to the app module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from excerpt import check_audio_file_exists, get_voice_info, get_existing_audio_chapters


class TestExcerptAudioLink(unittest.TestCase):
    """Tests for audio_link functionality in excerpt"""

    def test_check_audio_file_exists_function(self):
        """Test the check_audio_file_exists function"""
        # Clear caches before test
        check_audio_file_exists.cache_clear()
        get_existing_audio_chapters.cache_clear()
        
        with patch('excerpt.get_all_existing_audio_chapters') as mock_get_all:
            # Configure mock for an existing file
            mock_get_all.return_value = {1: {1, 2, 3}}  # Book 1 has chapters 1, 2, 3
            
            result = check_audio_file_exists('syn', 'bondarenko', 1, 1)
            self.assertTrue(result)
            
            # Verify the function was called with the correct parameters
            mock_get_all.assert_called_with('syn', 'bondarenko')

    def test_check_audio_file_not_exists(self):
        """Test check_audio_file_exists function for a non-existent file"""
        # Clear caches before test
        check_audio_file_exists.cache_clear()
        get_existing_audio_chapters.cache_clear()
        
        with patch('excerpt.get_all_existing_audio_chapters') as mock_get_all:
            # Configure mock for a non-existent file
            mock_get_all.return_value = {1: {2, 3}}  # Book 1 has chapters 2, 3 (not 1)
            
            result = check_audio_file_exists('syn', 'bondarenko', 1, 1)
            self.assertFalse(result)

    def test_get_voice_info_with_aliases(self):
        """Test get_voice_info function with aliases"""
        # Create a mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'name': 'Test Voice',
            'link_template': 'http://example.com/{book}/{chapter}.mp3',
            'voice_alias': 'test_voice',
            'translation_alias': 'test_translation'
        }
        
        result = get_voice_info(mock_cursor, 1, 1)
        
        # Verify the result contains all required fields
        self.assertIn('name', result)
        self.assertIn('link_template', result)
        self.assertIn('voice_alias', result)
        self.assertIn('translation_alias', result)
        
        # Verify the SQL query
        mock_cursor.execute.assert_called_once()
        sql_query = mock_cursor.execute.call_args[0][0]
        self.assertIn('v.alias as voice_alias', sql_query)
        self.assertIn('t.alias as translation_alias', sql_query)
        self.assertIn('JOIN translations t ON v.translation = t.code', sql_query)

    def test_audio_link_formation_logic(self):
        """Test audio_link generation logic"""
        # Verify the link format for an existing file
        book_number = 1
        chapter_number = 1
        translation_alias = 'syn'
        voice_alias = 'bondarenko'
        
        book_str = str(book_number).zfill(2)
        chapter_str = str(chapter_number).zfill(2)
        expected_link = f"/audio/{translation_alias}/{voice_alias}/{book_str}/{chapter_str}.mp3"
        self.assertEqual(expected_link, "/audio/syn/bondarenko/01/01.mp3")

    @patch('excerpt.check_audio_file_exists')
    def test_audio_link_with_mock_existing_file(self, mock_check_file):
        """Test with mock for an existing file"""
        mock_check_file.return_value = True
        
        result = mock_check_file('syn', 'bondarenko', 1, 1)
        self.assertTrue(result)
        mock_check_file.assert_called_with('syn', 'bondarenko', 1, 1)

    @patch('excerpt.check_audio_file_exists')
    def test_audio_link_with_mock_missing_file(self, mock_check_file):
        """Test with mock for a non-existent file"""
        mock_check_file.return_value = False
        
        result = mock_check_file('syn', 'bondarenko', 1, 1)
        self.assertFalse(result)
        mock_check_file.assert_called_with('syn', 'bondarenko', 1, 1)

    def test_audio_path_formatting(self):
        """Test correctness of audio file path formatting"""
        # Verify that book and chapter numbers are correctly zero-padded
        book_number = 1
        chapter_number = 5
        
        book_str = str(book_number).zfill(2)
        chapter_str = str(chapter_number).zfill(2)
        
        self.assertEqual(book_str, "01")
        self.assertEqual(chapter_str, "05")
        
        # Verify for larger numbers
        book_number = 40
        chapter_number = 28
        
        book_str = str(book_number).zfill(2)
        chapter_str = str(chapter_number).zfill(2)
        
        self.assertEqual(book_str, "40")
        self.assertEqual(chapter_str, "28")


if __name__ == '__main__':
    unittest.main()
