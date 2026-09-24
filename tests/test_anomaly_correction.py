import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

# Add the app directory to the path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from app.main import app
from app.models import AnomalyStatus, AnomalyStatusUpdateModel

client = TestClient(app)


class TestAnomalyCorrection:
    """Test suite for anomaly correction functionality"""
    
    def setup_method(self):
        """Setup test data"""
        self.test_anomaly_data = {
            'code': 1,
            'voice': 1,
            'translation': 1,
            'book_number': 43,  # John
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
            'verse_start_time': 10.5,
            'verse_end_time': 12.0,
            'verse_text': 'For God so loved the world...'
        }
    
    def test_anomaly_status_update_model_validation_corrected_requires_begin_end(self):
        """Test that CORRECTED status requires begin and end fields"""
        
        # Should raise validation error when begin/end are missing for CORRECTED
        with pytest.raises(ValidationError) as exc_info:
            AnomalyStatusUpdateModel(status=AnomalyStatus.CORRECTED)
        
        assert "begin and end are required for corrected status" in str(exc_info.value)
        
        # Should raise validation error when only begin is provided
        with pytest.raises(ValidationError) as exc_info:
            AnomalyStatusUpdateModel(status=AnomalyStatus.CORRECTED, begin=10.0)
        
        assert "begin and end are required for corrected status" in str(exc_info.value)
        
        # Should raise validation error when only end is provided
        with pytest.raises(ValidationError) as exc_info:
            AnomalyStatusUpdateModel(status=AnomalyStatus.CORRECTED, end=12.0)
        
        assert "begin and end are required for corrected status" in str(exc_info.value)
    
    def test_anomaly_status_update_model_validation_corrected_begin_less_than_end(self):
        """Test that begin must be less than end for CORRECTED status"""
        
        # Should raise validation error when begin >= end
        with pytest.raises(ValidationError) as exc_info:
            AnomalyStatusUpdateModel(status=AnomalyStatus.CORRECTED, begin=12.0, end=10.0)
        
        assert "begin must be less than end" in str(exc_info.value)
        
        # Should raise validation error when begin == end
        with pytest.raises(ValidationError) as exc_info:
            AnomalyStatusUpdateModel(status=AnomalyStatus.CORRECTED, begin=10.0, end=10.0)
        
        assert "begin must be less than end" in str(exc_info.value)
    
    def test_anomaly_status_update_model_validation_other_statuses_no_begin_end(self):
        """Test that other statuses cannot have begin/end fields"""
        
        # Should raise validation error for DETECTED with begin/end
        with pytest.raises(ValidationError) as exc_info:
            AnomalyStatusUpdateModel(status=AnomalyStatus.DETECTED, begin=10.0, end=12.0)
        
        assert "begin and end are only allowed for corrected status" in str(exc_info.value)
        
        # Should raise validation error for CONFIRMED with begin/end
        with pytest.raises(ValidationError) as exc_info:
            AnomalyStatusUpdateModel(status=AnomalyStatus.CONFIRMED, begin=10.0, end=12.0)
        
        assert "begin and end are only allowed for corrected status" in str(exc_info.value)
        
        # Should raise validation error for DISPROVED with begin/end
        with pytest.raises(ValidationError) as exc_info:
            AnomalyStatusUpdateModel(status=AnomalyStatus.DISPROVED, begin=10.0, end=12.0)
        
        assert "begin and end are only allowed for corrected status" in str(exc_info.value)
    
    def test_anomaly_status_update_model_validation_valid_corrected(self):
        """Test that valid CORRECTED status with begin/end passes validation"""
        
        # Should pass validation with valid begin/end
        model = AnomalyStatusUpdateModel(status=AnomalyStatus.CORRECTED, begin=10.0, end=12.0)
        assert model.status == AnomalyStatus.CORRECTED
        assert model.begin == 10.0
        assert model.end == 12.0
    
    def test_anomaly_status_update_model_validation_valid_other_statuses(self):
        """Test that other statuses without begin/end pass validation"""
        
        # Should pass validation for DETECTED without begin/end
        model = AnomalyStatusUpdateModel(status=AnomalyStatus.DETECTED)
        assert model.status == AnomalyStatus.DETECTED
        assert model.begin is None
        assert model.end is None
        
        # Should pass validation for CONFIRMED without begin/end
        model = AnomalyStatusUpdateModel(status=AnomalyStatus.CONFIRMED)
        assert model.status == AnomalyStatus.CONFIRMED
        assert model.begin is None
        assert model.end is None
    
    @patch('app.main.create_connection')
    def test_update_status_to_corrected_saves_custom_timing(self, mock_connection, admin_headers):
        """Test that updating status to CORRECTED saves custom begin/end times"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock fetchone to return anomaly data, then no existing fix, then updated anomaly
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly
            None,  # Second call - no existing manual fix
            self.test_anomaly_data   # Third call - return updated anomaly
        ]
        
        # Test data for correction
        correction_data = {
            "status": "corrected",
            "begin": 11.0,
            "end": 13.5
        }
        
        # Make request
        response = client.patch("/api/voices/anomalies/1/status", json=correction_data)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify database calls
        assert mock_cursor.execute.call_count == 5
        
        # Check that INSERT was called with corrected timing values
        insert_call = mock_cursor.execute.call_args_list[2]
        insert_query = insert_call[0][0]
        insert_params = insert_call[0][1]
        
        assert "INSERT INTO voice_manual_fixes" in insert_query
        assert insert_params[4] == 11.0  # begin time from request
        assert insert_params[5] == 13.5  # end time from request
        assert "Status: corrected" in insert_params[6]  # info field
    
    @patch('app.main.create_connection')
    def test_update_status_to_corrected_updates_existing_fix(self, mock_connection, admin_headers):
        """Test that updating status to CORRECTED updates existing manual fix with new timing"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock fetchone to return anomaly data, then existing fix, then updated anomaly
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly
            {'code': 123},  # Second call - existing manual fix
            self.test_anomaly_data   # Third call - return updated anomaly
        ]
        
        # Test data for correction
        correction_data = {
            "status": "corrected",
            "begin": 9.5,
            "end": 14.0
        }
        
        # Make request
        response = client.patch("/api/voices/anomalies/1/status", json=correction_data)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify database calls
        assert mock_cursor.execute.call_count == 5
        
        # Check that UPDATE was called with corrected timing values
        update_call = mock_cursor.execute.call_args_list[2]
        update_query = update_call[0][0]
        update_params = update_call[0][1]
        
        assert "UPDATE voice_manual_fixes" in update_query
        assert update_params[0] == 9.5   # begin time from request
        assert update_params[1] == 14.0  # end time from request
        assert "Status: corrected" in update_params[2]  # info field
        assert update_params[3] == 123   # existing fix code
    
    @patch('app.main.create_connection')
    def test_update_status_to_disproved_uses_original_timing(self, mock_connection):
        """Test that updating status to DISPROVED uses original timing from alignment"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock fetchone to return anomaly data, then no existing fix, then updated anomaly
        mock_cursor.fetchone.side_effect = [
            self.test_anomaly_data,  # First call - get anomaly
            None,  # Second call - no existing manual fix
            self.test_anomaly_data   # Third call - return updated anomaly
        ]
        
        # Test data for disproved (no begin/end should be provided)
        disproved_data = {
            "status": "disproved"
        }
        
        # Make request
        response = client.patch("/api/voices/anomalies/1/status", json=disproved_data)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify database calls
        assert mock_cursor.execute.call_count == 5
        
        # Check that INSERT was called with original timing values
        insert_call = mock_cursor.execute.call_args_list[2]
        insert_query = insert_call[0][0]
        insert_params = insert_call[0][1]
        
        assert "INSERT INTO voice_manual_fixes" in insert_query
        assert insert_params[4] == 10.5  # original verse_start_time
        assert insert_params[5] == 12.0  # original verse_end_time
        assert "Status: disproved" in insert_params[6]  # info field
    
    @patch('app.main.create_connection')
    def test_cannot_change_corrected_to_confirmed(self, mock_connection):
        """Test that changing status from corrected to confirmed is not allowed"""
        
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock anomaly with corrected status
        corrected_anomaly = self.test_anomaly_data.copy()
        corrected_anomaly['status'] = 'corrected'
        
        mock_cursor.fetchone.return_value = corrected_anomaly
        
        # Test data for changing to confirmed
        confirmed_data = {
            "status": "confirmed"
        }
        
        # Make request
        response = client.patch("/api/voices/anomalies/1/status", json=confirmed_data)
        
        # Verify response
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert "Cannot change status from corrected to confirmed" in error_detail
        
        # Verify that no database updates were attempted
        update_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'UPDATE voice_anomalies SET status' in str(call)]
        assert len(update_calls) == 0  # No status update should have been attempted
