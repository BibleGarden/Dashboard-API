import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from models import VoiceAnomalyCreateModel, AnomalyStatus


class TestCreateVoiceAnomaly:
    """Unit tests for create_voice_anomaly function"""
    
    @patch('main.create_connection')
    def test_create_anomaly_success(self, mock_create_connection):
        """Test successful anomaly creation"""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {'code': 1, 'translation': 1},  # voice exists
            {'code': 1},  # translation exists
            {'verse_exists': 1},  # verse exists
            {  # created anomaly
                'code': 1,
                'voice': 1,
                'translation': 1,
                'book_number': 1,
                'chapter_number': 1,
                'verse_number': 1,
                'word': 'test',
                'position_in_verse': 1,
                'position_from_end': None,
                'duration': 1.5,
                'speed': 2.0,
                'ratio': 1.5,
                'anomaly_type': 'manual',
                'status': 'detected',
                'verse_start_time': 10.0,
                'verse_end_time': 12.0,
                'verse_text': 'Test verse'
            }
        ]
        mock_cursor.lastrowid = 1
        
        # Import and test the function
        from main import create_voice_anomaly
        
        anomaly_data = VoiceAnomalyCreateModel(
            voice=1,
            translation=1,
            book_number=1,
            chapter_number=1,
            verse_number=1,
            word='test',
            position_in_verse=1,
            duration=1.5,
            speed=2.0,
            ratio=1.5,
            anomaly_type='manual'
        )
        
        result = create_voice_anomaly(anomaly_data)
        
        # Verify database calls
        assert mock_cursor.execute.call_count == 5
        mock_connection.commit.assert_called_once()
        
        # Verify result
        assert result['code'] == 1
        assert result['anomaly_type'] == 'manual'
        assert result['status'] == 'detected'
        assert 'translation_verse_id' not in mock_cursor.execute.call_args_list[3].args[0]

    @patch('main.create_connection')
    def test_create_anomaly_rejects_voice_translation_mismatch(self, mock_create_connection):
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {'code': 1, 'translation': 1},
            {'code': 16},
        ]

        from main import create_voice_anomaly

        anomaly_data = VoiceAnomalyCreateModel(
            voice=1, translation=16, book_number=43, chapter_number=3,
            verse_number=16, ratio=1.5,
        )
        with pytest.raises(HTTPException) as exc_info:
            create_voice_anomaly(anomaly_data)

        assert exc_info.value.status_code == 422
        assert 'Voice and anomaly translation must match' in str(exc_info.value.detail)
        assert mock_cursor.execute.call_count == 2
        mock_connection.rollback.assert_called_once()
    
    @patch('main.create_connection')
    def test_create_anomaly_voice_not_found(self, mock_create_connection):
        """Test error when voice doesn't exist"""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # voice not found
        
        from main import create_voice_anomaly
        
        anomaly_data = VoiceAnomalyCreateModel(
            voice=999,
            translation=1,
            book_number=1,
            chapter_number=1,
            verse_number=1,
            ratio=1.5
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_voice_anomaly(anomaly_data)
        
        assert exc_info.value.status_code == 404
        assert "Voice 999 not found" in str(exc_info.value.detail)
    
    @patch('main.create_connection')
    def test_create_anomaly_translation_not_found(self, mock_create_connection):
        """Test error when translation doesn't exist"""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {'code': 1, 'translation': 1},  # voice exists
            None  # translation not found
        ]
        
        from main import create_voice_anomaly
        
        anomaly_data = VoiceAnomalyCreateModel(
            voice=1,
            translation=999,
            book_number=1,
            chapter_number=1,
            verse_number=1,
            ratio=1.5
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_voice_anomaly(anomaly_data)
        
        assert exc_info.value.status_code == 404
        assert "Translation 999 not found" in str(exc_info.value.detail)
    
    @patch('main.create_connection')
    def test_create_anomaly_verse_not_found(self, mock_create_connection):
        """Test error when verse doesn't exist"""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_create_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {'code': 1, 'translation': 1},  # voice exists
            {'code': 1},  # translation exists
            None  # verse not found
        ]
        
        from main import create_voice_anomaly
        
        anomaly_data = VoiceAnomalyCreateModel(
            voice=1,
            translation=1,
            book_number=999,
            chapter_number=999,
            verse_number=999,
            ratio=1.5
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_voice_anomaly(anomaly_data)
        
        assert exc_info.value.status_code == 404
        assert "Verse not found" in str(exc_info.value.detail)
    
    def test_anomaly_create_model_validation(self):
        """Test VoiceAnomalyCreateModel validation"""
        # Test valid model
        valid_data = VoiceAnomalyCreateModel(
            voice=1,
            translation=1,
            book_number=1,
            chapter_number=1,
            verse_number=1,
            ratio=1.5,
            anomaly_type='manual'
        )
        assert valid_data.anomaly_type == 'manual'
        assert valid_data.status == AnomalyStatus.DETECTED
        
        # Test invalid anomaly_type
        with pytest.raises(ValueError) as exc_info:
            VoiceAnomalyCreateModel(
                voice=1,
                translation=1,
                book_number=1,
                chapter_number=1,
                verse_number=1,
                ratio=1.5,
                anomaly_type='invalid_type'
            )
        assert "Anomaly type must be one of" in str(exc_info.value)
        
        # Test invalid ratio
        with pytest.raises(ValueError) as exc_info:
            VoiceAnomalyCreateModel(
                voice=1,
                translation=1,
                book_number=1,
                chapter_number=1,
                verse_number=1,
                ratio=-1.0
            )
        assert "Ratio must be positive" in str(exc_info.value)
    
    def test_manual_anomaly_type_allowed(self):
        """Test that 'manual' is a valid anomaly type"""
        valid_types = ['fast', 'slow', 'long', 'short', 'manual']
        
        for anomaly_type in valid_types:
            model = VoiceAnomalyCreateModel(
                voice=1,
                translation=1,
                book_number=1,
                chapter_number=1,
                verse_number=1,
                ratio=1.5,
                anomaly_type=anomaly_type
            )
            assert model.anomaly_type == anomaly_type
