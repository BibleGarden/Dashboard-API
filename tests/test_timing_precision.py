import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the app directory to the path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


class TestTimingPrecision:
    """Test suite for timing precision in voice_manual_fixes operations"""
    
    def setup_method(self):
        """Setup test data with various timing scenarios"""
        self.base_anomaly_data = {
            'code': 1,
            'voice': 1,
            'translation': 1,
            'book_number': 43,
            'chapter_number': 3,
            'verse_number': 16,
            'word': 'test',
            'position_in_verse': 1,
            'position_from_end': 1,
            'duration': 1.5,
            'speed': 2.0,
            'ratio': 1.33,
            'anomaly_type': 'fast',
            'status': 'detected',
            'verse_start_time': 10.500,
            'verse_end_time': 12.000,
            'verse_text': 'Test verse'
        }
    
    @patch('app.main.create_connection')
    def test_timing_precision_exact_match(self, mock_connection):
        """Test that exact timing matches are handled correctly"""
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Existing fix with exact same timing
        existing_fix = {
            'code': 1,
            'begin': 10.500,  # Exact match
            'end': 12.000     # Exact match
        }
        
        mock_cursor.fetchone.side_effect = [
            self.base_anomaly_data,
            existing_fix,
            self.base_anomaly_data
        ]
        
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "confirmed"
        })
        
        assert response.status_code == 200
        
        # Verify DELETE was called
        calls = mock_cursor.execute.call_args_list
        delete_calls = [call for call in calls if 'DELETE FROM voice_manual_fixes' in call[0][0]]
        assert len(delete_calls) == 1
    
    @patch('app.main.create_connection')
    def test_timing_precision_within_tolerance(self, mock_connection):
        """Test that timing differences within tolerance (0.001) are accepted"""
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Existing fix with timing within tolerance
        existing_fix = {
            'code': 1,
            'begin': 10.5005,  # Difference of 0.0005 (within 0.001 tolerance)
            'end': 11.9995     # Difference of 0.0005 (within 0.001 tolerance)
        }
        
        mock_cursor.fetchone.side_effect = [
            self.base_anomaly_data,
            existing_fix,
            self.base_anomaly_data
        ]
        
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "confirmed"
        })
        
        assert response.status_code == 200
        
        # Verify DELETE was called (timing difference accepted)
        calls = mock_cursor.execute.call_args_list
        delete_calls = [call for call in calls if 'DELETE FROM voice_manual_fixes' in call[0][0]]
        assert len(delete_calls) == 1
    
    @patch('app.main.create_connection')
    def test_timing_precision_outside_tolerance(self, mock_connection):
        """Test that timing differences outside tolerance (0.001) cause error"""
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Existing fix with timing outside tolerance
        existing_fix = {
            'code': 1,
            'begin': 10.502,   # Difference of 0.002 (outside 0.001 tolerance)
            'end': 12.002      # Difference of 0.002 (outside 0.001 tolerance)
        }
        
        mock_cursor.fetchone.side_effect = [
            self.base_anomaly_data,
            existing_fix
        ]
        
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "confirmed"
        })
        
        assert response.status_code == 422
        response_data = response.json()
        assert "Cannot confirm anomaly" in response_data["detail"]
        assert "different timing" in response_data["detail"]
    
    @patch('app.main.create_connection')
    def test_timing_precision_one_value_within_one_outside(self, mock_connection):
        """Test case where one timing value is within tolerance but other is outside"""
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Existing fix with mixed timing precision
        existing_fix = {
            'code': 1,
            'begin': 10.5005,  # Within tolerance (0.0005 difference)
            'end': 12.005      # Outside tolerance (0.005 difference)
        }
        
        mock_cursor.fetchone.side_effect = [
            self.base_anomaly_data,
            existing_fix
        ]
        
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "confirmed"
        })
        
        assert response.status_code == 422
        response_data = response.json()
        assert "Cannot confirm anomaly" in response_data["detail"]
    
    @patch('app.main.create_connection')
    def test_decimal_precision_storage(self, mock_connection):
        """Test that decimal precision is maintained when storing manual fixes"""
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Anomaly with high precision timing
        precise_anomaly = self.base_anomaly_data.copy()
        precise_anomaly['verse_start_time'] = 10.123456
        precise_anomaly['verse_end_time'] = 12.987654
        
        mock_cursor.fetchone.side_effect = [
            precise_anomaly,
            None,  # No existing fix
            precise_anomaly
        ]
        
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "disproved"
        })
        
        assert response.status_code == 200
        
        # Verify INSERT was called with precise values
        calls = mock_cursor.execute.call_args_list
        insert_calls = [call for call in calls if 'INSERT INTO voice_manual_fixes' in call[0][0]]
        assert len(insert_calls) == 1
        
        insert_params = insert_calls[0][0][1]
        assert insert_params[4] == 10.123456  # begin with full precision
        assert insert_params[5] == 12.987654  # end with full precision
    
    @patch('app.main.create_connection')
    def test_zero_timing_values(self, mock_connection):
        """Test handling of zero timing values"""
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Anomaly with zero timing
        zero_timing_anomaly = self.base_anomaly_data.copy()
        zero_timing_anomaly['verse_start_time'] = 0.0
        zero_timing_anomaly['verse_end_time'] = 0.0
        
        mock_cursor.fetchone.side_effect = [
            zero_timing_anomaly,
            None,  # No existing fix
            zero_timing_anomaly
        ]
        
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "corrected",
            "begin": 0.0,
            "end": 1.0
        })
        
        assert response.status_code == 200
        
        # Verify INSERT was called with corrected values (not original zero values)
        calls = mock_cursor.execute.call_args_list
        insert_calls = [call for call in calls if 'INSERT INTO voice_manual_fixes' in call[0][0]]
        assert len(insert_calls) == 1
        
        insert_params = insert_calls[0][0][1]
        assert insert_params[4] == 0.0  # begin (from request)
        assert insert_params[5] == 1.0  # end (from request)
    
    @patch('app.main.create_connection')
    def test_negative_timing_values(self, mock_connection):
        """Test handling of negative timing values (edge case)"""
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Anomaly with negative timing (shouldn't happen in real data, but test edge case)
        negative_timing_anomaly = self.base_anomaly_data.copy()
        negative_timing_anomaly['verse_start_time'] = -1.0
        negative_timing_anomaly['verse_end_time'] = -0.5
        
        mock_cursor.fetchone.side_effect = [
            negative_timing_anomaly,
            None,  # No existing fix
            negative_timing_anomaly
        ]
        
        response = client.patch("/api/voices/anomalies/1/status", json={
            "status": "disproved"
        })
        
        assert response.status_code == 200
        
        # Verify INSERT was called even with negative values
        calls = mock_cursor.execute.call_args_list
        insert_calls = [call for call in calls if 'INSERT INTO voice_manual_fixes' in call[0][0]]
        assert len(insert_calls) == 1


if __name__ == "__main__":
    pytest.main([__file__])
