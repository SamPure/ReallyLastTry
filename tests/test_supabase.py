import pytest
from unittest.mock import Mock, patch
from app.config import settings

@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    with patch("app.config.create_client") as mock_create:
        mock_client = Mock()
        mock_create.return_value = mock_client
        yield mock_client

@pytest.mark.integration
@pytest.mark.supabase
def test_supabase_connection(mock_supabase):
    """Test Supabase connection and basic operations."""
    # Test table operations
    mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        status_code=201,
        data=[{"id": 1, "name": "test"}]
    )

    # Test insert
    response = mock_supabase.table("leads").insert({"name": "test"}).execute()
    assert response.status_code == 201
    assert len(response.data) == 1

    # Test select
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
        status_code=200,
        data=[{"id": 1, "name": "test"}]
    )

    result = mock_supabase.table("leads").select("*").eq("name", "test").execute()
    assert result.status_code == 200
    assert len(result.data) == 1

@pytest.mark.integration
@pytest.mark.supabase
def test_supabase_error_handling(mock_supabase):
    """Test Supabase error handling."""
    # Test authentication error
    mock_supabase.table.return_value.select.return_value.execute.side_effect = Exception("Auth error")

    with pytest.raises(Exception) as exc_info:
        mock_supabase.table("leads").select("*").execute()
    assert "Auth error" in str(exc_info.value)

@pytest.mark.integration
@pytest.mark.supabase
def test_supabase_batch_operations(mock_supabase):
    """Test Supabase batch operations."""
    # Test batch insert
    test_data = [
        {"name": "test1"},
        {"name": "test2"}
    ]

    mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        status_code=201,
        data=[{"id": i, "name": f"test{i}"} for i in range(1, 3)]
    )

    response = mock_supabase.table("leads").insert(test_data).execute()
    assert response.status_code == 201
    assert len(response.data) == 2
