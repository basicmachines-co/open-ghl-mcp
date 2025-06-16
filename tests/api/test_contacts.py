"""Tests for the api.contacts module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import httpx

from src.api.contacts import ContactsClient
from src.models.contact import Contact, ContactCreate, ContactUpdate, ContactList


class TestContactsClient:
    """Test cases for the ContactsClient class."""

    @pytest.fixture
    def mock_oauth_service(self):
        """Create a mock OAuth service."""
        service = Mock()
        service.get_valid_token = AsyncMock(return_value="test_token")
        service.get_location_token = AsyncMock(return_value="location_token")
        return service

    @pytest.fixture
    def contacts_client(self, mock_oauth_service):
        """Create a ContactsClient instance."""
        return ContactsClient(mock_oauth_service)

    @pytest.fixture
    def sample_contact_data(self):
        """Sample contact data for testing."""
        return {
            "id": "contact123",
            "locationId": "loc123",
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "tags": ["customer", "vip"],
            "dateAdded": datetime.now(timezone.utc).isoformat(),
            "dateUpdated": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.mark.asyncio
    async def test_get_contacts_basic(self, contacts_client):
        """Test getting contacts with basic parameters."""
        # Mock response data
        mock_contacts = [
            {"id": "1", "firstName": "John", "locationId": "loc123", "dateAdded": datetime.now(timezone.utc).isoformat()},
            {"id": "2", "firstName": "Jane", "locationId": "loc123", "dateAdded": datetime.now(timezone.utc).isoformat()},
        ]
        mock_response = Mock()
        mock_response.json.return_value = {
            "contacts": mock_contacts,
            "meta": {"total": 2},
            "traceId": "trace123"
        }

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await contacts_client.get_contacts("loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "GET",
                "/contacts",
                params={"locationId": "loc123", "limit": 100},
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, ContactList)
            assert len(result.contacts) == 2
            assert result.count == 2
            assert result.total == 2
            assert result.traceId == "trace123"

    @pytest.mark.asyncio
    async def test_get_contacts_with_filters(self, contacts_client):
        """Test getting contacts with various filters."""
        mock_response = Mock()
        mock_response.json.return_value = {"contacts": [], "meta": {"total": 0}}

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await contacts_client.get_contacts(
                location_id="loc123",
                limit=50,
                skip=10,
                query="john",
                email="john@example.com",
                phone="+1234567890",
                tags=["vip", "customer"]
            )

            # Verify request parameters
            mock_request.assert_called_once_with(
                "GET",
                "/contacts",
                params={
                    "locationId": "loc123",
                    "limit": 50,
                    "skip": 10,
                    "query": "john",
                    "email": "john@example.com",
                    "phone": "+1234567890",
                    "tags": "vip,customer"
                },
                location_id="loc123"
            )

    @pytest.mark.asyncio
    async def test_get_contacts_skip_zero_not_included(self, contacts_client):
        """Test that skip=0 is not included in params."""
        mock_response = Mock()
        mock_response.json.return_value = {"contacts": []}

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            await contacts_client.get_contacts("loc123", skip=0)

            # Verify skip is not in params when 0
            call_params = mock_request.call_args[1]["params"]
            assert "skip" not in call_params

    @pytest.mark.asyncio
    async def test_get_contact(self, contacts_client, sample_contact_data):
        """Test getting a specific contact."""
        mock_response = Mock()
        mock_response.json.return_value = {"contact": sample_contact_data}

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await contacts_client.get_contact("contact123", "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "GET",
                "/contacts/contact123",
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Contact)
            assert result.id == "contact123"
            assert result.firstName == "John"
            assert result.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_get_contact_without_wrapper(self, contacts_client, sample_contact_data):
        """Test getting a contact when API returns data without 'contact' wrapper."""
        mock_response = Mock()
        mock_response.json.return_value = sample_contact_data  # No wrapper

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await contacts_client.get_contact("contact123", "loc123")

            # Should still parse correctly
            assert isinstance(result, Contact)
            assert result.id == "contact123"

    @pytest.mark.asyncio
    async def test_create_contact(self, contacts_client, sample_contact_data):
        """Test creating a new contact."""
        contact_create = ContactCreate(
            locationId="loc123",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            tags=["new", "customer"]
        )

        mock_response = Mock()
        mock_response.json.return_value = {"contact": sample_contact_data}

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await contacts_client.create_contact(contact_create)

            # Verify request
            mock_request.assert_called_once_with(
                "POST",
                "/contacts",
                json={
                    "locationId": "loc123",
                    "firstName": "John",
                    "lastName": "Doe",
                    "email": "john@example.com",
                    "phone": "+1234567890",
                    "dnd": False,  # Default value from ContactCreate model
                    "tags": ["new", "customer"]
                },
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Contact)
            assert result.id == "contact123"

    @pytest.mark.asyncio
    async def test_update_contact(self, contacts_client, sample_contact_data):
        """Test updating an existing contact."""
        contact_update = ContactUpdate(
            firstName="Jane",
            email="jane@example.com",
            tags=["updated"]
        )

        mock_response = Mock()
        mock_response.json.return_value = {"contact": {**sample_contact_data, "firstName": "Jane"}}

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await contacts_client.update_contact("contact123", contact_update, "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "PUT",
                "/contacts/contact123",
                json={
                    "firstName": "Jane",
                    "email": "jane@example.com",
                    "tags": ["updated"]
                },
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Contact)
            assert result.firstName == "Jane"

    @pytest.mark.asyncio
    async def test_delete_contact_success(self, contacts_client):
        """Test successfully deleting a contact."""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await contacts_client.delete_contact("contact123", "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "DELETE",
                "/contacts/contact123",
                location_id="loc123"
            )

            # Verify result
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_contact_failure(self, contacts_client):
        """Test failed contact deletion."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await contacts_client.delete_contact("contact123", "loc123")

            # Should return False for non-200 status
            assert result is False

    @pytest.mark.asyncio
    async def test_add_contact_tags(self, contacts_client, sample_contact_data):
        """Test adding tags to a contact."""
        # Mock the tags request
        mock_tags_response = Mock()
        mock_tags_response.json.return_value = {"tags": ["customer", "vip", "new"], "tagsAdded": ["new"]}

        # Mock the get_contact call that follows
        mock_contact_response = Mock()
        mock_contact_response.json.return_value = {"contact": {**sample_contact_data, "tags": ["customer", "vip", "new"]}}

        with patch.object(contacts_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [mock_tags_response, mock_contact_response]

            result = await contacts_client.add_contact_tags("contact123", ["new"], "loc123")

            # Verify both requests were made
            assert mock_request.call_count == 2

            # Verify tags request
            mock_request.assert_any_call(
                "POST",
                "/contacts/contact123/tags",
                json={"tags": ["new"]},
                location_id="loc123"
            )

            # Verify get_contact request
            mock_request.assert_any_call(
                "GET",
                "/contacts/contact123",
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Contact)
            assert "new" in result.tags

    @pytest.mark.asyncio
    async def test_remove_contact_tags(self, contacts_client, sample_contact_data):
        """Test removing tags from a contact."""
        # Mock the tags request
        mock_tags_response = Mock()
        mock_tags_response.json.return_value = {"tags": ["customer"], "tagsRemoved": ["vip"]}

        # Mock the get_contact call that follows
        updated_contact_data = {**sample_contact_data, "tags": ["customer"]}
        mock_contact_response = Mock()
        mock_contact_response.json.return_value = {"contact": updated_contact_data}

        with patch.object(contacts_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [mock_tags_response, mock_contact_response]

            result = await contacts_client.remove_contact_tags("contact123", ["vip"], "loc123")

            # Verify both requests were made
            assert mock_request.call_count == 2

            # Verify tags request
            mock_request.assert_any_call(
                "DELETE",
                "/contacts/contact123/tags",
                json={"tags": ["vip"]},
                location_id="loc123"
            )

            # Verify get_contact request
            mock_request.assert_any_call(
                "GET",
                "/contacts/contact123",
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Contact)
            assert "vip" not in result.tags
            assert "customer" in result.tags

    @pytest.mark.asyncio
    async def test_get_contacts_empty_response(self, contacts_client):
        """Test handling empty contacts response."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # Empty response

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await contacts_client.get_contacts("loc123")

            # Should handle gracefully
            assert isinstance(result, ContactList)
            assert result.contacts == []
            assert result.count == 0
            assert result.total is None

    @pytest.mark.asyncio
    async def test_contact_list_with_meta_total(self, contacts_client):
        """Test ContactList uses meta.total when available."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "contacts": [{"id": "1", "locationId": "loc123", "dateAdded": datetime.now(timezone.utc).isoformat()}],
            "meta": {"total": 100}  # More than actual contacts returned
        }

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await contacts_client.get_contacts("loc123")

            assert result.count == 1  # Actual contacts in response
            assert result.total == 100  # Total from meta

    @pytest.mark.asyncio
    async def test_contact_list_fallback_total(self, contacts_client):
        """Test ContactList falls back to top-level total when meta.total not available."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "contacts": [{"id": "1", "locationId": "loc123", "dateAdded": datetime.now(timezone.utc).isoformat()}],
            "total": 50  # Top-level total
        }

        with patch.object(contacts_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await contacts_client.get_contacts("loc123")

            assert result.total == 50