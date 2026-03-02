"""
Integration tests for batch anomaly status update functionality.
Tests that updating status of one anomaly updates all anomalies of the same verse.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models import AnomalyStatus


class TestBatchAnomalyUpdateIntegration:
    """Integration tests for batch anomaly status update"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)

    @patch('app.main.create_connection')
    def test_patch_anomaly_status_updates_all_verse_anomalies(self, mock_create_connection):
        """Test that PATCH request updates all anomalies of the same verse"""
        # Setup mock connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock anomaly data
        anomaly_data = {
            'code': 123,
            'voice': 1,
            'translation': 1,
            'book_number': 1,
            'chapter_number': 1,
            'verse_number': 1,
            'word': 'test',
            'position_in_verse': 1,
            'position_from_end': 1,
            'duration': 1.5,
            'speed': 2.0,
            'ratio': 1.0,
            'anomaly_type': 'speed',
            'status': 'detected',
            'translation_verse_id': 'verse_1',
            'verse_start_time': 10.0,
            'verse_end_time': 12.0,
            'verse_text': 'Test verse'
        }
        
        # Mock cursor.fetchone() calls
        mock_cursor.fetchone.side_effect = [
            anomaly_data,  # First call - get anomaly details
            None,          # No existing manual fix for CONFIRMED status
            anomaly_data   # Third call - return updated anomaly
        ]
        
        # Make PATCH request
        response = self.client.patch(
            "/api/voices/anomalies/123/status",
            json={"status": "confirmed"}
        )
        
        # Verify response
        assert response.status_code == 200
        
        # Verify the UPDATE query was called with verse parameters
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE voice_anomalies' in str(call)]
        
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        # Check that the UPDATE query uses verse parameters
        query = update_call[0][0]
        params = update_call[0][1]
        
        assert 'WHERE voice = %s AND book_number = %s AND chapter_number = %s AND verse_number = %s' in query
        assert params == ('confirmed', 1, 1, 1, 1)

    @patch('app.main.create_connection')
    def test_patch_anomaly_status_disproved_updates_all_verse_anomalies(self, mock_create_connection):
        """Test that DISPROVED status updates all anomalies of the same verse"""
        # Setup mock connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock anomaly data
        anomaly_data = {
            'code': 456,
            'voice': 2,
            'translation': 1,
            'book_number': 2,
            'chapter_number': 3,
            'verse_number': 5,
            'word': 'word',
            'position_in_verse': 2,
            'position_from_end': 3,
            'duration': 2.1,
            'speed': 1.8,
            'ratio': 0.9,
            'anomaly_type': 'duration',
            'status': 'detected',
            'translation_verse_id': 'verse_2',
            'verse_start_time': 25.5,
            'verse_end_time': 28.3,
            'verse_text': 'Test verse'
        }
        
        # Mock cursor.fetchone() calls
        mock_cursor.fetchone.side_effect = [
            anomaly_data,  # First call - get anomaly details
            None,          # No existing manual fix
            anomaly_data   # Return updated anomaly
        ]
        
        # Make PATCH request
        response = self.client.patch(
            "/api/voices/anomalies/456/status",
            json={"status": "disproved"}
        )
        
        # Verify response
        assert response.status_code == 200
        
        # Verify the UPDATE query was called with verse parameters
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE voice_anomalies' in str(call)]
        
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        # Check that the UPDATE query uses verse parameters
        query = update_call[0][0]
        params = update_call[0][1]
        
        assert 'WHERE voice = %s AND book_number = %s AND chapter_number = %s AND verse_number = %s' in query
        assert params == ('disproved', 2, 2, 3, 5)

    @patch('app.main.create_connection')
    def test_patch_anomaly_status_corrected_updates_all_verse_anomalies(self, mock_create_connection):
        """Test that CORRECTED status with timing updates all anomalies of the same verse"""
        # Setup mock connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock anomaly data
        anomaly_data = {
            'code': 789,
            'voice': 3,
            'translation': 1,
            'book_number': 3,
            'chapter_number': 7,
            'verse_number': 12,
            'word': 'corrected',
            'position_in_verse': 1,
            'position_from_end': 1,
            'duration': 1.2,
            'speed': 2.5,
            'ratio': 1.1,
            'anomaly_type': 'speed',
            'status': 'detected',
            'translation_verse_id': 'verse_3',
            'verse_start_time': 45.0,
            'verse_end_time': 48.0,
            'verse_text': 'Corrected verse'
        }
        
        # Mock cursor.fetchone() calls
        mock_cursor.fetchone.side_effect = [
            anomaly_data,  # First call - get anomaly details
            None,          # No existing manual fix
            anomaly_data   # Return updated anomaly
        ]
        
        # Make PATCH request with corrected timing
        response = self.client.patch(
            "/api/voices/anomalies/789/status",
            json={
                "status": "corrected",
                "begin": 45.2,
                "end": 47.8
            }
        )
        
        # Verify response
        assert response.status_code == 200
        
        # Verify the UPDATE query was called with verse parameters
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE voice_anomalies' in str(call)]
        
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        # Check that the UPDATE query uses verse parameters
        query = update_call[0][0]
        params = update_call[0][1]
        
        assert 'WHERE voice = %s AND book_number = %s AND chapter_number = %s AND verse_number = %s' in query
        assert params == ('corrected', 3, 3, 7, 12)

    @patch('app.main.create_connection')
    def test_patch_anomaly_status_different_verses_not_affected(self, mock_create_connection):
        """Test that anomalies from different verses are not affected"""
        # Setup mock connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock anomaly data for verse 1
        anomaly_data = {
            'code': 100,
            'voice': 4,
            'translation': 1,
            'book_number': 1,
            'chapter_number': 1,
            'verse_number': 1,  # Verse 1
            'word': 'test',
            'position_in_verse': 1,
            'position_from_end': 1,
            'duration': 1.5,
            'speed': 2.0,
            'ratio': 1.0,
            'anomaly_type': 'speed',
            'status': 'detected',
            'translation_verse_id': 'verse_1',
            'verse_start_time': 10.0,
            'verse_end_time': 12.0,
            'verse_text': 'Test verse 1'
        }
        
        # Mock cursor.fetchone() calls
        mock_cursor.fetchone.side_effect = [
            anomaly_data,  # First call - get anomaly details
            None,          # No existing manual fix for CONFIRMED status
            anomaly_data   # Third call - return updated anomaly
        ]
        
        # Make PATCH request
        response = self.client.patch(
            "/api/voices/anomalies/100/status",
            json={"status": "confirmed"}
        )
        
        # Verify response
        assert response.status_code == 200
        
        # Verify the UPDATE query was called with specific verse parameters
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE voice_anomalies' in str(call)]
        
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        # Check that the UPDATE query uses specific verse parameters (only verse 1)
        query = update_call[0][0]
        params = update_call[0][1]
        
        assert 'WHERE voice = %s AND book_number = %s AND chapter_number = %s AND verse_number = %s' in query
        assert params == ('confirmed', 4, 1, 1, 1)  # Only verse 1 should be affected
