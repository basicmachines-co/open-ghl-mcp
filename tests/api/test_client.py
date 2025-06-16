"""Unit tests for GoHighLevel API client with composition pattern"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from src.api.client import GoHighLevelClient
from src.models.contact import Contact, ContactCreate, ContactList
from src.models.conversation import MessageCreate, MessageType, Message
from src.utils.exceptions import (
    DuplicateResourceError,
)


class TestGoHighLevelClient:
    """Test GoHighLevel API client with composition pattern"""

    @pytest.fixture
    def mock_oauth_service(self):
        """Create mock OAuth service"""
        service = Mock()
        service.get_valid_token = AsyncMock(return_value="agency_token")
        service.get_location_token = AsyncMock(return_value="location_token")
        return service

    @pytest.fixture
    def client(self, mock_oauth_service):
        """Create API client instance"""
        return GoHighLevelClient(mock_oauth_service)

    @pytest.fixture
    def mock_contact(self):
        """Create a mock contact for testing"""
        return Contact(
            id="test_contact_id",
            locationId="test_location",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            dateAdded=datetime.now(timezone.utc),
            tags=["test"],
        )

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_oauth_service):
        """Test that client initializes specialized clients properly"""
        client = GoHighLevelClient(mock_oauth_service)

        # Check that specialized clients are initialized
        assert hasattr(client, "_contacts")
        assert hasattr(client, "_conversations")
        assert hasattr(client, "_opportunities")
        assert hasattr(client, "_calendars")

        # Check OAuth service is set
        assert client.oauth_service == mock_oauth_service

    @pytest.mark.asyncio
    async def test_get_contacts_delegation(self, client, mock_contact):
        """Test that get_contacts properly delegates to contacts client"""
        # Mock the contacts client
        mock_contacts_result = ContactList(contacts=[mock_contact], count=1, total=1)

        with patch.object(
            client._contacts, "get_contacts", return_value=mock_contacts_result
        ) as mock_get:
            result = await client.get_contacts("test_location", limit=10)

        # Verify delegation
        mock_get.assert_called_once_with(
            location_id="test_location",
            limit=10,
            skip=0,
            query=None,
            email=None,
            phone=None,
            tags=None,
        )

        # Verify result
        assert len(result.contacts) == 1
        assert result.contacts[0].id == mock_contact.id
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_get_contact_delegation(self, client, mock_contact):
        """Test that get_contact properly delegates to contacts client"""
        with patch.object(
            client._contacts, "get_contact", return_value=mock_contact
        ) as mock_get:
            result = await client.get_contact("test_contact_id", "test_location")

        # Verify delegation
        mock_get.assert_called_once_with("test_contact_id", "test_location")

        # Verify result
        assert result.id == mock_contact.id
        assert result.firstName == "John"

    @pytest.mark.asyncio
    async def test_create_contact_delegation(self, client, mock_contact):
        """Test that create_contact properly delegates to contacts client"""
        contact_data = ContactCreate(
            locationId="test_location",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
        )

        with patch.object(
            client._contacts, "create_contact", return_value=mock_contact
        ) as mock_create:
            result = await client.create_contact(contact_data)

        # Verify delegation
        mock_create.assert_called_once_with(contact_data)

        # Verify result
        assert result.id == mock_contact.id
        assert result.firstName == "John"

    @pytest.mark.asyncio
    async def test_send_message_delegation(self, client):
        """Test that send_message properly delegates to conversations client"""
        message_data = MessageCreate(
            type=MessageType.EMAIL,
            conversationId="conv123",
            contactId="contact123",
            html="<p>Test email</p>",
            subject="Test Subject",
            text="Test email",
        )

        mock_message = Message(
            id="msg123",
            conversationId="conv123",
            contactId="contact123",
            body="Test email",
            type=2,  # Email type
            status="sent",
        )

        with patch.object(
            client._conversations, "send_message", return_value=mock_message
        ) as mock_send:
            result = await client.send_message("conv123", message_data, "test_location")

        # Verify delegation
        mock_send.assert_called_once_with("conv123", message_data, "test_location")

        # Verify result
        assert result.conversationId == "conv123"
        assert result.id == "msg123"

    @pytest.mark.asyncio
    async def test_error_propagation(self, client):
        """Test that errors from specialized clients are properly propagated"""
        contact_data = ContactCreate(
            locationId="test_location", email="existing@example.com"
        )

        # Mock the contacts client to raise an error
        with patch.object(
            client._contacts,
            "create_contact",
            side_effect=DuplicateResourceError("Contact already exists", 400),
        ):
            with pytest.raises(DuplicateResourceError) as exc_info:
                await client.create_contact(contact_data)

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_manager_support(self, mock_oauth_service):
        """Test that client properly supports async context manager"""
        client = GoHighLevelClient(mock_oauth_service)

        # Mock the specialized clients' context manager methods
        with patch.object(
            client._contacts, "__aenter__", return_value=client._contacts
        ) as mock_contacts_enter:
            with patch.object(
                client._contacts, "__aexit__", return_value=None
            ) as mock_contacts_exit:
                with patch.object(
                    client._conversations,
                    "__aenter__",
                    return_value=client._conversations,
                ) as mock_conv_enter:
                    with patch.object(
                        client._conversations, "__aexit__", return_value=None
                    ) as mock_conv_exit:
                        with patch.object(
                            client._opportunities,
                            "__aenter__",
                            return_value=client._opportunities,
                        ) as mock_opp_enter:
                            with patch.object(
                                client._opportunities, "__aexit__", return_value=None
                            ) as mock_opp_exit:
                                with patch.object(
                                    client._calendars,
                                    "__aenter__",
                                    return_value=client._calendars,
                                ) as mock_cal_enter:
                                    with patch.object(
                                        client._calendars,
                                        "__aexit__",
                                        return_value=None,
                                    ) as mock_cal_exit:

                                        async with client:
                                            pass  # Just test the context manager

                        # Verify all specialized clients were entered and exited
                        mock_contacts_enter.assert_called_once()
                        mock_contacts_exit.assert_called_once()
                        mock_conv_enter.assert_called_once()
                        mock_conv_exit.assert_called_once()
                        mock_opp_enter.assert_called_once()
                        mock_opp_exit.assert_called_once()
                        mock_cal_enter.assert_called_once()
                        mock_cal_exit.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_contact_methods_exist(self, client):
        """Test that all expected contact methods exist and are callable"""
        contact_methods = [
            "get_contacts",
            "get_contact",
            "create_contact",
            "update_contact",
            "delete_contact",
            "add_contact_tags",
            "remove_contact_tags",
        ]

        for method_name in contact_methods:
            assert hasattr(client, method_name), f"Missing method: {method_name}"
            assert callable(
                getattr(client, method_name)
            ), f"Method not callable: {method_name}"

    @pytest.mark.asyncio
    async def test_all_conversation_methods_exist(self, client):
        """Test that all expected conversation methods exist and are callable"""
        conversation_methods = [
            "get_conversations",
            "get_conversation",
            "create_conversation",
            "get_messages",
            "send_message",
            "update_message_status",
        ]

        for method_name in conversation_methods:
            assert hasattr(client, method_name), f"Missing method: {method_name}"
            assert callable(
                getattr(client, method_name)
            ), f"Method not callable: {method_name}"

    @pytest.mark.asyncio
    async def test_all_opportunity_methods_exist(self, client):
        """Test that all expected opportunity methods exist and are callable"""
        opportunity_methods = [
            "get_opportunities",
            "get_opportunity",
            "create_opportunity",
            "update_opportunity",
            "delete_opportunity",
            "update_opportunity_status",
            "get_pipelines",
        ]

        for method_name in opportunity_methods:
            assert hasattr(client, method_name), f"Missing method: {method_name}"
            assert callable(
                getattr(client, method_name)
            ), f"Method not callable: {method_name}"

    @pytest.mark.asyncio
    async def test_all_calendar_methods_exist(self, client):
        """Test that all expected calendar methods exist and are callable"""
        calendar_methods = [
            "get_appointments",
            "get_appointment",
            "create_appointment",
            "update_appointment",
            "delete_appointment",
            "get_calendars",
            "get_calendar",
            "get_free_slots",
        ]

        for method_name in calendar_methods:
            assert hasattr(client, method_name), f"Missing method: {method_name}"
            assert callable(
                getattr(client, method_name)
            ), f"Method not callable: {method_name}"

    @pytest.mark.asyncio
    async def test_location_methods_exist(self, client):
        """Test that location methods exist and are callable"""
        location_methods = ["get_locations", "get_location"]

        for method_name in location_methods:
            assert hasattr(client, method_name), f"Missing method: {method_name}"
            assert callable(
                getattr(client, method_name)
            ), f"Method not callable: {method_name}"


class TestSpecializedClientIntegration:
    """Test that the specialized clients work correctly when accessed directly"""

    @pytest.fixture
    def mock_oauth_service(self):
        """Create mock OAuth service"""
        service = Mock()
        service.get_valid_token = AsyncMock(return_value="agency_token")
        service.get_location_token = AsyncMock(return_value="location_token")
        return service

    @pytest.mark.asyncio
    async def test_contacts_client_accessible(self, mock_oauth_service):
        """Test that contacts client is accessible and properly initialized"""
        from src.api.contacts import ContactsClient

        client = GoHighLevelClient(mock_oauth_service)

        assert isinstance(client._contacts, ContactsClient)
        assert client._contacts.oauth_service == mock_oauth_service

    @pytest.mark.asyncio
    async def test_conversations_client_accessible(self, mock_oauth_service):
        """Test that conversations client is accessible and properly initialized"""
        from src.api.conversations import ConversationsClient

        client = GoHighLevelClient(mock_oauth_service)

        assert isinstance(client._conversations, ConversationsClient)
        assert client._conversations.oauth_service == mock_oauth_service

    @pytest.mark.asyncio
    async def test_opportunities_client_accessible(self, mock_oauth_service):
        """Test that opportunities client is accessible and properly initialized"""
        from src.api.opportunities import OpportunitiesClient

        client = GoHighLevelClient(mock_oauth_service)

        assert isinstance(client._opportunities, OpportunitiesClient)
        assert client._opportunities.oauth_service == mock_oauth_service

    @pytest.mark.asyncio
    async def test_calendars_client_accessible(self, mock_oauth_service):
        """Test that calendars client is accessible and properly initialized"""
        from src.api.calendars import CalendarsClient

        client = GoHighLevelClient(mock_oauth_service)

        assert isinstance(client._calendars, CalendarsClient)
        assert client._calendars.oauth_service == mock_oauth_service
