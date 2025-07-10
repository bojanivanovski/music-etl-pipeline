"""Basic tests to verify setup is working."""

def test_basic_math():
    """Simple test to verify pytest is working."""
    assert 1 + 1 == 2

def test_imports():
    """Test that we can import basic packages."""
    import os
    import sys
    assert True

def test_project_structure():
    """Test that project directories exist."""
    import os
    assert os.path.exists('ingestion')
    assert os.path.exists('databricks')
    assert os.path.exists('airflow')
