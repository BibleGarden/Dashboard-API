import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add the app directory to the path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from app.main import app
from app.models import AnomalyStatus

client = TestClient(app)


class TestVoiceManualFixes:
    """Test suite for voice_manual_fixes integration with anomaly status updates"""
    
    def setup_method(self):
        """Setup test data"""
        self.test_anomaly_data = {
            'code': 1,
            'voice': 1,
            'translation': 1,
            'book_number': 43,  # John
            'chapter_number': 3,
            'verse_number': 16,  # Now NOT NULL
            'word': 'test',  # Can be None now
            'position_in_verse': 1,
            'position_from_end': 1,
            'duration': 1.5,  # Can be None now
            'speed': 2.0,  # Can be None now
            'ratio': 1.33,
            'anomaly_type': 'fast',  # Now NOT NULL
            'status': 'detected',
            'verse_start_time': 10.5,
            'verse_end_time': 12.0,
            'verse_text': 'For God so loved the world...'
        }
    
    @patch('app.main.create_connection')
    def test_update_status_to_disproved_creates_manual_fix(self, mock_connection):
        """Test that updating status to DISPROVED creates a record in voice_manual_fixes"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly data
            None,  # Second call - no existing manual fix
            self.test_anomaly_data   # Third call - return updated anomaly
        ]
        
        # Make request to update status
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "disproved"
        })
        
        # Check response
        assert response.status_code == 200
        
        # Verify database calls
        calls = mock_cursor.execute.call_args_list
        
        # Should have calls for: get anomaly, check existing fix, insert new fix, update status, get updated anomaly
        assert len(calls) >= 4
        
        # Check that INSERT was called for voice_manual_fixes
        insert_call = None
        for call in calls:
            if 'INSERT INTO voice_manual_fixes' in call[0][0]:
                insert_call = call
                break
        
        assert insert_call is not None
        insert_params = insert_call[0][1]
        assert insert_params[0] == 1  # voice
        assert insert_params[1] == 43  # book_number
        assert insert_params[2] == 3   # chapter_number
        assert insert_params[3] == 16  # verse_number
        assert insert_params[4] == 10.5  # begin
        assert insert_params[5] == 12.0  # end
        assert "disproved" in insert_params[6].lower()  # info
    
    @patch('app.main.create_connection')
    def test_update_status_to_corrected_creates_manual_fix(self, mock_connection):
        """Test that updating status to CORRECTED creates a record in voice_manual_fixes"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly data
            None,  # Second call - no existing manual fix
            self.test_anomaly_data   # Third call - return updated anomaly
        ]
        
        # Make request to update status
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "corrected",
            "begin": 10.0,
            "end": 12.5
        })
        
        # Check response
        assert response.status_code == 200
        
        # Verify INSERT was called for voice_manual_fixes
        calls = mock_cursor.execute.call_args_list
        insert_call = None
        for call in calls:
            if 'INSERT INTO voice_manual_fixes' in call[0][0]:
                insert_call = call
                break
        
        assert insert_call is not None
        insert_params = insert_call[0][1]
        assert "corrected" in insert_params[6].lower()  # info should contain status
    
    @patch('app.main.create_connection')
    def test_update_status_to_confirmed_deletes_matching_manual_fix(self, mock_connection):
        """Test that updating status to CONFIRMED deletes matching record from voice_manual_fixes"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock existing manual fix with matching times
        existing_fix = {
            'code': 1,
            'begin': 10.5,  # Matches verse_start_time
            'end': 12.0     # Matches verse_end_time
        }
        
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly data
            existing_fix,            # Second call - existing manual fix
            self.test_anomaly_data   # Third call - return updated anomaly
        ]
        
        # Make request to update status
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "confirmed"
        })
        
        # Check response
        assert response.status_code == 200
        
        # Verify DELETE was called for voice_manual_fixes
        calls = mock_cursor.execute.call_args_list
        delete_call = None
        for call in calls:
            if 'DELETE FROM voice_manual_fixes' in call[0][0]:
                delete_call = call
                break
        
        assert delete_call is not None
        delete_params = delete_call[0][1]
        assert delete_params[0] == 1  # Should delete record with code=1
    
    @patch('app.main.create_connection')
    def test_update_status_to_confirmed_with_mismatched_times_returns_error(self, mock_connection):
        """Test that updating status to CONFIRMED with mismatched times returns error"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock existing manual fix with different times
        existing_fix = {
            'code': 1,
            'begin': 15.0,  # Different from verse_start_time (10.5)
            'end': 17.0     # Different from verse_end_time (12.0)
        }
        
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly data
            existing_fix             # Second call - existing manual fix with different times
        ]
        
        # Make request to update status
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "confirmed"
        })
        
        # Check response - should return error
        assert response.status_code == 422
        response_data = response.json()
        assert "Cannot confirm anomaly" in response_data["detail"]
        assert "manual fix exists with different timing" in response_data["detail"]
    
    @patch('app.main.create_connection')
    def test_update_existing_manual_fix_when_disproved_again(self, mock_connection):
        """Test that updating status to DISPROVED updates existing manual fix record"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock existing manual fix
        existing_fix = {'code': 1}
        
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly data
            existing_fix,            # Second call - existing manual fix
            self.test_anomaly_data   # Third call - return updated anomaly
        ]
        
        # Make request to update status
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "disproved"
        })
        
        # Check response
        assert response.status_code == 200
        
        # Verify UPDATE was called for voice_manual_fixes (not INSERT)
        calls = mock_cursor.execute.call_args_list
        update_call = None
        insert_call = None
        
        for call in calls:
            if 'UPDATE voice_manual_fixes' in call[0][0]:
                update_call = call
            elif 'INSERT INTO voice_manual_fixes' in call[0][0]:
                insert_call = call
        
        assert update_call is not None  # Should update existing record
        assert insert_call is None      # Should not insert new record
        
        update_params = update_call[0][1]
        assert update_params[0] == 10.5  # begin
        assert update_params[1] == 12.0  # end
        assert "disproved" in update_params[2].lower()  # info
        assert update_params[3] == 1     # code of existing record
    
    @patch('app.main.create_connection')
    def test_update_status_without_timing_data_skips_manual_fixes(self, mock_connection):
        """Test that updating status works even when verse timing data is missing"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Anomaly data without timing information
        anomaly_without_timing = self.test_anomaly_data.copy()
        anomaly_without_timing['verse_start_time'] = None
        anomaly_without_timing['verse_end_time'] = None
        
        mock_cursor.fetchone.side_effect = [
            anomaly_without_timing,  # First call - get anomaly data without timing
            anomaly_without_timing   # Second call - return updated anomaly
        ]
        
        # Make request to update status
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "disproved"
        })
        
        # Check response
        assert response.status_code == 200
        
        # Verify no voice_manual_fixes operations were attempted
        calls = mock_cursor.execute.call_args_list
        manual_fixes_calls = [call for call in calls 
                             if 'voice_manual_fixes' in call[0][0]]
        
        assert len(manual_fixes_calls) == 0  # No manual fixes operations
    
    @patch('app.main.create_connection')
    def test_decimal_float_type_conversion_in_confirmed_status(self, mock_connection):
        """Test that decimal/float type conversion works correctly when comparing timing values"""
        
        from decimal import Decimal
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock existing manual fix with Decimal values (as returned from database)
        existing_fix = {
            'code': 1,
            'begin': Decimal('10.500'),  # Decimal type from database
            'end': Decimal('12.000')     # Decimal type from database
        }
        
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly data (float values)
            existing_fix,            # Second call - existing manual fix (Decimal values)
            self.test_anomaly_data   # Third call - return updated anomaly
        ]
        
        # Make request to update status
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "confirmed"
        })
        
        # Check response - should succeed without type conversion errors
        assert response.status_code == 200
        
        # Verify DELETE was called (values should match after conversion)
        calls = mock_cursor.execute.call_args_list
        delete_calls = [call for call in calls if 'DELETE FROM voice_manual_fixes' in call[0][0]]
        assert len(delete_calls) == 1
    
    @patch('app.main.create_connection')
    def test_update_status_with_null_values_in_anomaly(self, mock_connection):
        """Test that updating status works with NULL values in nullable fields"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Anomaly data with NULL values in nullable fields
        anomaly_with_nulls = self.test_anomaly_data.copy()
        anomaly_with_nulls['word'] = None  # Nullable field
        anomaly_with_nulls['duration'] = None  # Nullable field
        anomaly_with_nulls['speed'] = None  # Nullable field
        # verse_number remains NOT NULL
        # anomaly_type remains NOT NULL
        
        mock_cursor.fetchone.side_effect = [
            anomaly_with_nulls,  # First call - get anomaly data with NULLs
            None,  # Second call - no existing manual fix
            anomaly_with_nulls   # Third call - return updated anomaly
        ]
        
        # Make request to update status
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "disproved"
        })
        
        # Check response - should succeed even with NULL values
        assert response.status_code == 200
        
        # Verify INSERT was called for voice_manual_fixes
        calls = mock_cursor.execute.call_args_list
        insert_calls = [call for call in calls if 'INSERT INTO voice_manual_fixes' in call[0][0]]
        assert len(insert_calls) == 1
    
    @patch('app.main.create_connection')
    def test_already_resolved_status_cannot_be_set_manually(self, mock_create_connection):
        """Test that already_resolved status cannot be set manually"""
        
        # Setup mock database connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock anomaly data
        mock_anomaly = {
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
            'ratio': 1.5,
            'anomaly_type': 'fast',
            'status': 'detected',
            'verse_start_time': 10.0,
            'verse_end_time': 15.0,
            'verse_text': 'Test verse'
        }
        
        # Configure mock to return anomaly data
        mock_cursor.fetchone.return_value = mock_anomaly
        
        # Make request to update status to already_resolved
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "already_resolved"
        })
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
        
        # Check error message
        data = response.json()
        assert "Cannot manually set status to already_resolved or disproved_whisper" in data["detail"]
        
        # Verify that no UPDATE query was executed (since we return error before updating)
        calls = mock_cursor.execute.call_args_list
        update_calls = [call for call in calls if 'UPDATE voice_anomalies SET status' in call[0][0]]
        assert len(update_calls) == 0


if __name__ == "__main__":
    pytest.main([__file__])
