"""Tests for the mcp.tools.contacts module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.models.contact import Contact, ContactList
from src.mcp.params.contacts import (
    CreateContactParams,
    UpdateContactParams,
    DeleteContactParams,
    GetContactParams,
    SearchContactsParams,
    ManageTagsParams,
)
from src.mcp.tools.contacts import _register_contact_tools


class TestContactTools:
    """Test cases for contact tools."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP instance."""
        mock = Mock()
        mock.tool = Mock(return_value=lambda func: func)
        return mock

    @pytest.fixture
    def mock_get_client(self):
        """Create a mock get_client function."""
        mock_client = AsyncMock()
        
        async def get_client(access_token=None):
            return mock_client
        
        return get_client, mock_client

    @pytest.fixture
    def setup_tools(self, mock_mcp, mock_get_client):
        """Set up contact tools with mocks."""
        get_client_func, mock_client = mock_get_client
        
        # Capture the registered tools
        tools = {}
        
        def mock_tool_decorator():
            def decorator(func):
                # Store the function by its name
                tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool_decorator
        
        # Register the tools
        _register_contact_tools(mock_mcp, get_client_func)
        
        return tools, mock_client

    @pytest.mark.asyncio
    async def test_create_contact(self, setup_tools):
        """Test create_contact tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            contactName="John Doe",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc),
            tags=["new", "customer"],
            source="website"
        )
        mock_client.create_contact.return_value = mock_contact
        
        # Create params
        params = CreateContactParams(
            location_id="loc123",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+1234567890",
            tags=["new", "customer"],
            source="website",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["create_contact"](params)
        
        # Verify
        assert result["success"] is True
        assert result["contact"]["id"] == "contact123"
        assert result["contact"]["firstName"] == "John"
        mock_client.create_contact.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_contact_with_custom_fields(self, setup_tools):
        """Test create_contact with custom fields."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            contactName="John Doe",
            firstName="John",
            email="john@example.com",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc),
            customFields=[{"key": "field1", "value": "value1"}]
        )
        mock_client.create_contact.return_value = mock_contact
        
        # Create params with custom fields
        params = CreateContactParams(
            location_id="loc123",
            first_name="John",
            email="john@example.com",
            custom_fields={"field1": "value1"},
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["create_contact"](params)
        
        # Verify custom fields were passed
        assert result["success"] is True
        create_call_args = mock_client.create_contact.call_args[0][0]
        assert create_call_args.customFields == [{"key": "field1", "value": "value1"}]

    @pytest.mark.asyncio
    async def test_update_contact(self, setup_tools):
        """Test update_contact tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            contactName="Jane Doe",
            firstName="Jane",
            lastName="Doe",
            email="jane@example.com",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.update_contact.return_value = mock_contact
        
        # Create params
        params = UpdateContactParams(
            contact_id="contact123",
            location_id="loc123",
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["update_contact"](params)
        
        # Verify
        assert result["success"] is True
        assert result["contact"]["firstName"] == "Jane"
        assert result["contact"]["email"] == "jane@example.com"
        mock_client.update_contact.assert_called_once_with(
            "contact123", 
            mock_client.update_contact.call_args[0][1],  # The update data
            "loc123"
        )

    @pytest.mark.asyncio
    async def test_update_contact_with_custom_fields(self, setup_tools):
        """Test update_contact with custom fields."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            contactName="John Doe",
            email="john@example.com",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.update_contact.return_value = mock_contact
        
        # Create params
        params = UpdateContactParams(
            contact_id="contact123",
            location_id="loc123",
            custom_fields={"field1": "new_value"},
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["update_contact"](params)
        
        # Verify custom fields were passed
        assert result["success"] is True
        update_data = mock_client.update_contact.call_args[0][1]
        assert update_data.customFields == [{"key": "field1", "value": "new_value"}]

    @pytest.mark.asyncio
    async def test_delete_contact_success(self, setup_tools):
        """Test delete_contact tool with success."""
        tools, mock_client = setup_tools
        
        # Mock successful deletion
        mock_client.delete_contact.return_value = True
        
        # Create params
        params = DeleteContactParams(
            contact_id="contact123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["delete_contact"](params)
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Contact deleted successfully"
        mock_client.delete_contact.assert_called_once_with("contact123", "loc123")

    @pytest.mark.asyncio
    async def test_delete_contact_failure(self, setup_tools):
        """Test delete_contact tool with failure."""
        tools, mock_client = setup_tools
        
        # Mock failed deletion
        mock_client.delete_contact.return_value = False
        
        # Create params
        params = DeleteContactParams(
            contact_id="contact123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["delete_contact"](params)
        
        # Verify
        assert result["success"] is False
        assert result["message"] == "Failed to delete contact"

    @pytest.mark.asyncio
    async def test_get_contact(self, setup_tools):
        """Test get_contact tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            contactName="John Doe",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.get_contact.return_value = mock_contact
        
        # Create params
        params = GetContactParams(
            contact_id="contact123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_contact"](params)
        
        # Verify
        assert result["success"] is True
        assert result["contact"]["id"] == "contact123"
        assert result["contact"]["firstName"] == "John"
        mock_client.get_contact.assert_called_once_with("contact123", "loc123")

    @pytest.mark.asyncio
    async def test_search_contacts(self, setup_tools):
        """Test search_contacts tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_contacts = [
            Contact(
                id="contact1",
                locationId="loc123",
                contactName="John Doe",
                email="john@example.com",
                dateAdded=datetime.now(timezone.utc),
                dateUpdated=datetime.now(timezone.utc)
            ),
            Contact(
                id="contact2",
                locationId="loc123",
                contactName="Jane Smith",
                email="jane@example.com",
                dateAdded=datetime.now(timezone.utc),
                dateUpdated=datetime.now(timezone.utc)
            )
        ]
        mock_result = ContactList(contacts=mock_contacts, count=2, total=10)
        mock_client.get_contacts.return_value = mock_result
        
        # Create params
        params = SearchContactsParams(
            location_id="loc123",
            query="example.com",
            limit=10,
            skip=0,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["search_contacts"](params)
        
        # Verify
        assert result["success"] is True
        assert len(result["contacts"]) == 2
        assert result["count"] == 2
        assert result["total"] == 10
        mock_client.get_contacts.assert_called_once_with(
            location_id="loc123",
            limit=10,
            skip=0,
            query="example.com",
            email=None,
            phone=None,
            tags=None
        )

    @pytest.mark.asyncio
    async def test_search_contacts_with_filters(self, setup_tools):
        """Test search_contacts with multiple filters."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_result = ContactList(contacts=[], count=0, total=0)
        mock_client.get_contacts.return_value = mock_result
        
        # Create params with filters
        params = SearchContactsParams(
            location_id="loc123",
            email="john@example.com",
            phone="+1234567890",
            tags=["vip", "customer"],
            limit=20,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["search_contacts"](params)
        
        # Verify filters were passed
        assert result["success"] is True
        mock_client.get_contacts.assert_called_once_with(
            location_id="loc123",
            limit=20,
            skip=0,
            query=None,
            email="john@example.com",
            phone="+1234567890",
            tags=["vip", "customer"]
        )

    @pytest.mark.asyncio
    async def test_add_contact_tags(self, setup_tools):
        """Test add_contact_tags tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            contactName="John Doe",
            email="john@example.com",
            tags=["customer", "vip", "premium"],
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.add_contact_tags.return_value = mock_contact
        
        # Create params
        params = ManageTagsParams(
            contact_id="contact123",
            location_id="loc123",
            tags=["vip", "premium"],
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["add_contact_tags"](params)
        
        # Verify
        assert result["success"] is True
        assert "vip" in result["contact"]["tags"]
        assert "premium" in result["contact"]["tags"]
        mock_client.add_contact_tags.assert_called_once_with(
            "contact123", ["vip", "premium"], "loc123"
        )

    @pytest.mark.asyncio
    async def test_remove_contact_tags(self, setup_tools):
        """Test remove_contact_tags tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            contactName="John Doe",
            email="john@example.com",
            tags=["customer"],  # vip removed
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.remove_contact_tags.return_value = mock_contact
        
        # Create params
        params = ManageTagsParams(
            contact_id="contact123",
            location_id="loc123",
            tags=["vip"],
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["remove_contact_tags"](params)
        
        # Verify
        assert result["success"] is True
        assert "vip" not in result["contact"]["tags"]
        assert "customer" in result["contact"]["tags"]
        mock_client.remove_contact_tags.assert_called_once_with(
            "contact123", ["vip"], "loc123"
        )