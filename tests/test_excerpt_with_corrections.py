import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add the app directory to the path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from app.main import app
from app.excerpt import get_excerpt_with_alignment, get_chapter_data

client = TestClient(app)


class TestExcerptWithCorrections:
    """Test suite for excerpt_with_alignment with voice_manual_fixes corrections"""
    
    def test_excerpt_with_alignment_sql_query_structure(self):
        """Test that the SQL query includes proper JOIN with voice_manual_fixes"""
        
        # This test verifies the SQL query structure by checking the source code
        # After refactoring, the SQL is in get_chapter_data()
        import inspect
        
        # Get the source code of the get_chapter_data function
        source = inspect.getsource(get_chapter_data)
        
        # Verify that the query includes voice_manual_fixes JOIN
        assert 'LEFT JOIN voice_manual_fixes vmf' in source
        assert 'COALESCE(vmf.begin, a.begin) as begin' in source
        assert 'COALESCE(vmf.end, a.end) as end' in source
        assert 'vmf.voice' in source
        assert 'vmf.book_number' in source
        assert 'vmf.chapter_number' in source
        assert 'vmf.verse_number' in source
    
    def test_excerpt_with_alignment_endpoint_exists(self):
        """Test that the excerpt_with_alignment endpoint exists and is accessible"""
        
        # Test with a request that should return 422 (invalid data) rather than 404 (not found)
        response = client.get("/api/excerpt_with_alignment", params={
            "translation": 999999,  # Non-existent translation
            "excerpt": "jhn 3:16"
        })
        
        # Should return 422 (validation error) not 404 (endpoint not found)
        assert response.status_code == 422
        assert "not found" in response.json()["detail"].lower()
    
    def test_excerpt_with_alignment_query_uses_table_aliases(self):
        """Test that the SQL query uses proper table aliases to avoid ambiguity"""
        
        import inspect
        
        # Get the source code of the get_chapter_data function
        source = inspect.getsource(get_chapter_data)
        
        # Verify that table aliases are used properly
        assert 'v.chapter_number' in source
        assert 'v.verse_number' in source
        
        # Verify that the query doesn't have ambiguous column references
        # (verify that table aliases are used)
        assert 'translation_verses v' in source or 'translation_verses AS v' in source
    
    def test_excerpt_with_alignment_coalesce_logic(self):
        """Test that COALESCE logic is implemented correctly in the query"""
        
        import inspect
        
        # Get the source code of the get_chapter_data function
        source = inspect.getsource(get_chapter_data)
        
        # Verify COALESCE logic: voice_manual_fixes takes priority over voice_alignments
        assert 'COALESCE(vmf.begin, a.begin) as begin' in source
        assert 'COALESCE(vmf.end, a.end) as end' in source
        
        # Verify that both tables are properly joined
        assert 'LEFT JOIN voice_alignments a' in source or 'LEFT JOIN voice_alignments AS a' in source
        assert 'LEFT JOIN voice_manual_fixes vmf' in source
