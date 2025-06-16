"""Tests for the mcp.resources.contacts module."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from src.models.contact import Contact, ContactList
from src.mcp.resources.contacts import _register_contact_resources


class TestContactResources:
    """Test cases for contact-related MCP resources."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP instance."""
        mock = Mock()
        mock.resource = Mock(return_value=lambda func: func)
        return mock

    @pytest.fixture
    def mock_ghl_client(self):
        """Create a mock GoHighLevel client."""
        return AsyncMock()

    @pytest.fixture
    def setup_resources(self, mock_mcp, mock_ghl_client):
        """Set up contact resources with mocks."""
        # Capture the registered resources
        resources = {}
        
        def mock_resource_decorator(uri_template):
            def decorator(func):
                # Store the function by its URI template
                resources[uri_template] = func
                return func
            return decorator
        
        mock_mcp.resource = mock_resource_decorator
        
        # Register the resources
        _register_contact_resources(mock_mcp, mock_ghl_client)
        
        return resources, mock_ghl_client

    @pytest.mark.asyncio
    async def test_list_contacts_resource(self, setup_resources):
        """Test list_contacts_resource."""
        resources, mock_client = setup_resources
        
        # Mock the client response
        mock_contacts = [
            Contact(
                id="contact1",
                locationId="loc123",
                firstName="John",
                lastName="Doe",
                email="john@example.com",
                phone="+1234567890",
                tags=["customer", "vip"],
                dateAdded=datetime.now(timezone.utc),
                dateUpdated=datetime.now(timezone.utc),
                source="Website"
            ),
            Contact(
                id="contact2",
                locationId="loc123",
                firstName="Jane",
                lastName="Smith",
                email="jane@example.com",
                phone="+0987654321",
                tags=["prospect"],
                dateAdded=datetime.now(timezone.utc),
                dateUpdated=datetime.now(timezone.utc),
                source="Referral"
            ),
            Contact(
                id="contact3",
                locationId="loc123",
                name="Bob Wilson",  # Using name field instead of firstName/lastName
                email="bob@example.com",
                dateAdded=datetime.now(timezone.utc),
                dateUpdated=datetime.now(timezone.utc)
            )
        ]
        mock_result = ContactList(contacts=mock_contacts, count=3, total=3)
        mock_client.get_contacts.return_value = mock_result
        
        # Call the resource function
        resource_func = resources["contacts://{location_id}"]
        result = await resource_func("loc123")
        
        # Verify the output format
        assert "# Contacts for Location loc123" in result
        assert "Total contacts: 3" in result
        assert "## John Doe" in result
        assert "## Jane Smith" in result
        assert "## Bob Wilson" in result
        assert "- ID: contact1" in result
        assert "- Email: john@example.com" in result
        assert "- Phone: +1234567890" in result
        assert "- Tags: customer, vip" in result
        assert "- Email: jane@example.com" in result
        assert "- Tags: prospect" in result
        
        # Verify client was called correctly
        mock_client.get_contacts.assert_called_once_with(location_id="loc123", limit=100)

    @pytest.mark.asyncio
    async def test_list_contacts_resource_with_unknown_contact(self, setup_resources):
        """Test list_contacts_resource with contact that has no name fields."""
        resources, mock_client = setup_resources
        
        # Mock contact with minimal information
        mock_contacts = [
            Contact(
                id="contact1",
                locationId="loc123",
                email="unknown@example.com",
                dateAdded=datetime.now(timezone.utc),
                dateUpdated=datetime.now(timezone.utc)
            )
        ]
        mock_result = ContactList(contacts=mock_contacts, count=1, total=1)
        mock_client.get_contacts.return_value = mock_result
        
        # Call the resource function
        resource_func = resources["contacts://{location_id}"]
        result = await resource_func("loc123")
        
        # Verify unknown contact handling
        assert "## Unknown" in result
        assert "- Email: unknown@example.com" in result
        assert "- Phone: N/A" in result

    @pytest.mark.asyncio
    async def test_list_contacts_resource_client_not_initialized(self, setup_resources):
        """Test list_contacts_resource when client is None."""
        resources, _ = setup_resources
        
        # Register with None client to simulate uninitialized state
        _register_contact_resources(Mock(), None)
        
        # Call the resource function
        resource_func = resources["contacts://{location_id}"]
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="MCP server not properly initialized"):
            await resource_func("loc123")

    @pytest.mark.asyncio
    async def test_get_contact_resource(self, setup_resources):
        """Test get_contact_resource."""
        resources, mock_client = setup_resources
        
        # Mock the client response
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            tags=["customer", "vip"],
            source="Website",
            companyName="Acme Corp",
            address1="123 Main St",
            city="Anytown",
            state="CA",
            postalCode="12345",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.get_contact.return_value = mock_contact
        
        # Call the resource function
        resource_func = resources["contact://{location_id}/{contact_id}"]
        result = await resource_func("loc123", "contact123")
        
        # Verify the output format
        assert "# Contact: John Doe" in result
        assert "- ID: contact123" in result
        assert "- Location: loc123" in result
        assert "- Email: john@example.com" in result
        assert "- Phone: +1234567890" in result
        assert "- Tags: customer, vip" in result
        assert "- Source: Website" in result
        assert "- Company: Acme Corp" in result
        assert "- Address: 123 Main St" in result
        assert "- City: Anytown" in result
        assert "- State: CA" in result
        assert "- Postal Code: 12345" in result
        assert "- Date Added:" in result
        assert "- Last Updated:" in result
        
        # Verify client was called correctly
        mock_client.get_contact.assert_called_once_with("contact123", "loc123")

    @pytest.mark.asyncio
    async def test_get_contact_resource_minimal_fields(self, setup_resources):
        """Test get_contact_resource with minimal contact information."""
        resources, mock_client = setup_resources
        
        # Mock contact with minimal fields
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            name="Bob Wilson",  # Only has name field
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.get_contact.return_value = mock_contact
        
        # Call the resource function
        resource_func = resources["contact://{location_id}/{contact_id}"]
        result = await resource_func("loc123", "contact123")
        
        # Verify minimal fields handling
        assert "# Contact: Bob Wilson" in result
        assert "- Email: N/A" in result
        assert "- Phone: N/A" in result
        # Should not contain optional fields
        assert "- Tags:" not in result
        assert "- Source:" not in result
        assert "- Company:" not in result
        assert "- Address:" not in result

    @pytest.mark.asyncio
    async def test_get_contact_resource_unknown_name(self, setup_resources):
        """Test get_contact_resource with no name fields."""
        resources, mock_client = setup_resources
        
        # Mock contact with no name information
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            email="mystery@example.com",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.get_contact.return_value = mock_contact
        
        # Call the resource function
        resource_func = resources["contact://{location_id}/{contact_id}"]
        result = await resource_func("loc123", "contact123")
        
        # Verify unknown name handling
        assert "# Contact: Unknown" in result

    @pytest.mark.asyncio
    async def test_get_contact_resource_client_not_initialized(self, setup_resources):
        """Test get_contact_resource when client is None."""
        resources, _ = setup_resources
        
        # Register with None client to simulate uninitialized state
        _register_contact_resources(Mock(), None)
        
        # Call the resource function
        resource_func = resources["contact://{location_id}/{contact_id}"]
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="MCP server not properly initialized"):
            await resource_func("loc123", "contact123")

    @pytest.mark.asyncio
    async def test_get_contact_resource_with_firstName_lastName_combination(self, setup_resources):
        """Test get_contact_resource with firstName and lastName combination."""
        resources, mock_client = setup_resources
        
        # Mock contact with first and last name but no name field
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            firstName="Alice",
            lastName="Johnson",
            email="alice@example.com",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.get_contact.return_value = mock_contact
        
        # Call the resource function
        resource_func = resources["contact://{location_id}/{contact_id}"]
        result = await resource_func("loc123", "contact123")
        
        # Verify name combination
        assert "# Contact: Alice Johnson" in result

    @pytest.mark.asyncio
    async def test_get_contact_resource_with_only_firstName(self, setup_resources):
        """Test get_contact_resource with only firstName."""
        resources, mock_client = setup_resources
        
        # Mock contact with only firstName
        mock_contact = Contact(
            id="contact123",
            locationId="loc123",
            firstName="Charlie",
            email="charlie@example.com",
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc)
        )
        mock_client.get_contact.return_value = mock_contact
        
        # Call the resource function
        resource_func = resources["contact://{location_id}/{contact_id}"]
        result = await resource_func("loc123", "contact123")
        
        # Verify firstName only
        assert "# Contact: Charlie" in result