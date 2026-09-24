"""
Tests for batch anomaly status update functionality.
Tests that updating status of one anomaly updates all anomalies of the same verse.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.main import update_anomaly_status
from app.models import AnomalyStatusUpdateModel, AnomalyStatus


class TestBatchAnomalyUpdate:
    """Test batch update of anomaly status for all anomalies of the same verse"""

    @patch('app.main.create_connection')
    def test_update_status_affects_all_verse_anomalies(self, mock_create_connection):
        """Test that updating one anomaly status updates all anomalies of the same verse"""
        # Setup mock connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock anomaly data
        anomaly_data = {
            'code': 1,
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
        
        # Create update request
        update_data = AnomalyStatusUpdateModel(status=AnomalyStatus.CONFIRMED)
        
        # Call the function
        result = update_anomaly_status(1, update_data)
        
        # Verify the UPDATE query was called with verse parameters, not just anomaly code
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE voice_anomalies' in str(call)]
        
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        # Check that the UPDATE query uses verse parameters
        query = update_call[0][0]
        params = update_call[0][1]
        
        assert 'WHERE voice = %s AND book_number = %s AND chapter_number = %s AND verse_number = %s' in query
        assert params == ('confirmed', 'confirmed', 1, 1, 1, 1)

        # Verify commit was called
        mock_connection.commit.assert_called_once()

    @patch('app.main.create_connection')
    def test_disproved_status_updates_all_verse_anomalies(self, mock_create_connection):
        """Test that DISPROVED status updates all anomalies of the same verse"""
        # Setup mock connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock anomaly data
        anomaly_data = {
            'code': 1,
            'voice': 2,
            'translation': 1,
            'book_number': 2,
            'chapter_number': 3,
            'verse_number': 4,
            'word': 'test',
            'position_in_verse': 1,
            'position_from_end': 1,
            'duration': 1.5,
            'speed': 2.0,
            'ratio': 1.0,
            'anomaly_type': 'duration',
            'status': 'detected',
            'verse_start_time': 15.0,
            'verse_end_time': 18.0,
            'verse_text': 'Another test verse'
        }
        
        # Mock cursor.fetchone() calls
        mock_cursor.fetchone.side_effect = [
            anomaly_data,  # First call - get anomaly details
            None,          # No existing manual fix
            anomaly_data   # Return updated anomaly
        ]
        
        # Create update request
        update_data = AnomalyStatusUpdateModel(status=AnomalyStatus.DISPROVED)
        
        # Call the function
        result = update_anomaly_status(1, update_data)
        
        # Verify the UPDATE query was called with correct verse parameters
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE voice_anomalies' in str(call)]
        
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        # Check that the UPDATE query uses verse parameters
        query = update_call[0][0]
        params = update_call[0][1]
        
        assert 'WHERE voice = %s AND book_number = %s AND chapter_number = %s AND verse_number = %s' in query
        assert params == ('disproved', 'disproved', 2, 2, 3, 4)

    @patch('app.main.create_connection')
    def test_corrected_status_updates_all_verse_anomalies(self, mock_create_connection):
        """Test that CORRECTED status updates all anomalies of the same verse"""
        # Setup mock connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock anomaly data
        anomaly_data = {
            'code': 1,
            'voice': 3,
            'translation': 1,
            'book_number': 1,
            'chapter_number': 5,
            'verse_number': 10,
            'word': 'test',
            'position_in_verse': 1,
            'position_from_end': 1,
            'duration': 1.5,
            'speed': 2.0,
            'ratio': 1.0,
            'anomaly_type': 'speed',
            'status': 'detected',
            'verse_start_time': 20.0,
            'verse_end_time': 23.0,
            'verse_text': 'Corrected test verse'
        }
        
        # Mock cursor.fetchone() calls
        mock_cursor.fetchone.side_effect = [
            anomaly_data,  # First call - get anomaly details
            None,          # No existing manual fix
            anomaly_data   # Return updated anomaly
        ]
        
        # Create update request with corrected timing
        update_data = AnomalyStatusUpdateModel(
            status=AnomalyStatus.CORRECTED,
            begin=20.5,
            end=22.8
        )
        
        # Call the function
        result = update_anomaly_status(1, update_data)
        
        # Verify the UPDATE query was called with correct verse parameters
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE voice_anomalies' in str(call)]
        
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        # Check that the UPDATE query uses verse parameters
        query = update_call[0][0]
        params = update_call[0][1]
        
        assert 'WHERE voice = %s AND book_number = %s AND chapter_number = %s AND verse_number = %s' in query
        assert params == ('corrected', 'corrected', 3, 1, 5, 10)
