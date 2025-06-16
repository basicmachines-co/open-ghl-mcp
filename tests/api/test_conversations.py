"""Tests for the api.conversations module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.api.conversations import ConversationsClient
from src.models.conversation import (
    Conversation,
    ConversationCreate,
    ConversationList,
    Message,
    MessageCreate,
    MessageList,
    MessageType,
)


class TestConversationsClient:
    """Test cases for the ConversationsClient class."""

    @pytest.fixture
    def mock_oauth_service(self):
        """Create a mock OAuth service."""
        service = Mock()
        service.get_valid_token = AsyncMock(return_value="test_token")
        service.get_location_token = AsyncMock(return_value="location_token")
        return service

    @pytest.fixture
    def conversations_client(self, mock_oauth_service):
        """Create a ConversationsClient instance."""
        return ConversationsClient(mock_oauth_service)

    @pytest.fixture
    def sample_conversation_data(self):
        """Sample conversation data for testing."""
        return {
            "id": "conv123",
            "locationId": "loc123",
            "contactId": "contact123",
            "type": "SMS",
            "unreadCount": 2,
            "lastMessageDate": int(datetime.now(timezone.utc).timestamp() * 1000),  # Unix timestamp in milliseconds
            "lastMessageType": "TYPE_SMS",  # String type as API returns
            "lastMessageBody": "Hello there",
            "starred": False,
        }

    @pytest.fixture
    def sample_message_data(self):
        """Sample message data for testing."""
        return {
            "id": "msg123",
            "conversationId": "conv123",
            "locationId": "loc123",
            "contactId": "contact123",
            "type": 1,  # SMS
            "body": "Test message",
            "status": "delivered",
            "direction": "outbound",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.mark.asyncio
    async def test_get_conversations_basic(self, conversations_client):
        """Test getting conversations with basic parameters."""
        mock_conversations = [
            {"id": "conv1", "locationId": "loc123", "contactId": "contact1", "type": "SMS"},
            {"id": "conv2", "locationId": "loc123", "contactId": "contact2", "type": "Email"},
        ]
        mock_response = Mock()
        mock_response.json.return_value = {
            "conversations": mock_conversations,
            "total": 2
        }

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await conversations_client.get_conversations("loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "GET",
                "/conversations/search",
                params={"location_id": "loc123", "limit": 100},
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, ConversationList)
            assert len(result.conversations) == 2
            assert result.count == 2
            assert result.total == 2

    @pytest.mark.asyncio
    async def test_get_conversations_with_filters(self, conversations_client):
        """Test getting conversations with various filters."""
        mock_response = Mock()
        mock_response.json.return_value = {"conversations": [], "total": 0}

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await conversations_client.get_conversations(
                location_id="loc123",
                limit=50,
                skip=10,
                contact_id="contact123",
                starred=True,
                unread_only=True
            )

            # Verify request parameters
            mock_request.assert_called_once_with(
                "GET",
                "/conversations/search",
                params={
                    "location_id": "loc123",
                    "limit": 50,
                    "skip": 10,
                    "contactId": "contact123",
                    "starred": True,
                    "unreadOnly": True
                },
                location_id="loc123"
            )

    @pytest.mark.asyncio
    async def test_get_conversations_skip_zero_not_included(self, conversations_client):
        """Test that skip=0 is not included in params."""
        mock_response = Mock()
        mock_response.json.return_value = {"conversations": []}

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            await conversations_client.get_conversations("loc123", skip=0)

            # Verify skip is not in params when 0
            call_params = mock_request.call_args[1]["params"]
            assert "skip" not in call_params

    @pytest.mark.asyncio
    async def test_get_conversation(self, conversations_client, sample_conversation_data):
        """Test getting a specific conversation."""
        mock_response = Mock()
        mock_response.json.return_value = sample_conversation_data  # Direct response

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await conversations_client.get_conversation("conv123", "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "GET",
                "/conversations/conv123",
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Conversation)
            assert result.id == "conv123"
            assert result.contactId == "contact123"

    @pytest.mark.asyncio
    async def test_create_conversation(self, conversations_client, sample_conversation_data):
        """Test creating a new conversation."""
        conversation_create = ConversationCreate(
            locationId="loc123",
            contactId="contact123",
            lastMessageType=MessageType.SMS
        )

        mock_response = Mock()
        mock_response.json.return_value = {"conversation": sample_conversation_data}

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await conversations_client.create_conversation(conversation_create)

            # Verify request
            mock_request.assert_called_once_with(
                "POST",
                "/conversations",
                json={
                    "locationId": "loc123",
                    "contactId": "contact123",
                    "lastMessageType": "SMS"
                },
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Conversation)
            assert result.id == "conv123"

    @pytest.mark.asyncio
    async def test_create_conversation_without_wrapper(self, conversations_client, sample_conversation_data):
        """Test creating conversation when API returns data without wrapper."""
        conversation_create = ConversationCreate(
            locationId="loc123",
            contactId="contact123",
            lastMessageType=MessageType.EMAIL
        )

        mock_response = Mock()
        mock_response.json.return_value = sample_conversation_data  # No wrapper

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await conversations_client.create_conversation(conversation_create)

            # Should still parse correctly
            assert isinstance(result, Conversation)
            assert result.id == "conv123"

    @pytest.mark.asyncio
    async def test_get_messages_basic(self, conversations_client, sample_message_data):
        """Test getting messages for a conversation."""
        mock_messages = [sample_message_data, {**sample_message_data, "id": "msg124"}]
        mock_response = Mock()
        mock_response.json.return_value = {
            "messages": mock_messages,
            "total": 2
        }

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await conversations_client.get_messages("conv123", "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "GET",
                "/conversations/conv123/messages",
                params={"limit": 100},
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, MessageList)
            assert len(result.messages) == 2
            assert result.count == 2
            assert result.total == 2

    @pytest.mark.asyncio
    async def test_get_messages_nested_structure(self, conversations_client, sample_message_data):
        """Test getting messages with nested response structure."""
        mock_messages = [sample_message_data]
        mock_response = Mock()
        mock_response.json.return_value = {
            "messages": {
                "messages": mock_messages,
                "total": 1
            }
        }

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await conversations_client.get_messages("conv123", "loc123")

            # Should handle nested structure
            assert isinstance(result, MessageList)
            assert len(result.messages) == 1
            assert result.count == 1

    @pytest.mark.asyncio
    async def test_get_messages_with_skip(self, conversations_client):
        """Test getting messages with skip parameter."""
        mock_response = Mock()
        mock_response.json.return_value = {"messages": []}

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            await conversations_client.get_messages("conv123", "loc123", limit=50, skip=20)

            # Verify skip is included when > 0
            mock_request.assert_called_once_with(
                "GET",
                "/conversations/conv123/messages",
                params={"limit": 50, "skip": 20},
                location_id="loc123"
            )

    @pytest.mark.asyncio
    async def test_send_message_sms(self, conversations_client):
        """Test sending an SMS message."""
        message = MessageCreate(
            type=MessageType.SMS,
            conversationId="conv123",
            contactId="contact123",
            message="Test SMS",
            phone="+1234567890"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "conversationId": "conv123",
            "messageId": "msg125"
        }

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await conversations_client.send_message("conv123", message, "loc123")

            # Verify request - phone should be at top level as phoneNumber
            mock_request.assert_called_once_with(
                "POST",
                "/conversations/messages",
                json={
                    "conversationId": "conv123",
                    "type": "SMS",
                    "contactId": "contact123",
                    "message": "Test SMS",
                    "phoneNumber": "+1234567890"  # Changed from phone to phoneNumber
                },
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Message)
            assert result.id == "msg125"
            assert result.conversationId == "conv123"
            assert result.body == "Test SMS"
            assert result.type == 1  # SMS type as int
            assert result.status == "sent"

    @pytest.mark.asyncio
    async def test_send_message_email(self, conversations_client):
        """Test sending an email message."""
        message = MessageCreate(
            type=MessageType.EMAIL,
            conversationId="conv123",
            contactId="contact123",
            message="Test email body",
            subject="Test Subject",
            html="<p>Test email body</p>"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "conversationId": "conv123",
            "messageId": "msg126"
        }

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await conversations_client.send_message("conv123", message, "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "POST",
                "/conversations/messages",
                json={
                    "conversationId": "conv123",
                    "type": "Email",
                    "contactId": "contact123",
                    "message": "Test email body",
                    "subject": "Test Subject",
                    "html": "<p>Test email body</p>"
                },
                location_id="loc123"
            )

            # Verify result
            assert result.type == 2  # Email type as int

    @pytest.mark.asyncio
    async def test_send_message_without_phone(self, conversations_client):
        """Test sending message without phone field."""
        message = MessageCreate(
            type=MessageType.WHATSAPP,
            conversationId="conv123",
            contactId="contact123",
            message="Test WhatsApp"
        )

        mock_response = Mock()
        mock_response.json.return_value = {"conversationId": "conv123", "messageId": "msg127"}

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await conversations_client.send_message("conv123", message, "loc123")

            # Verify phone field is not included
            call_json = mock_request.call_args[1]["json"]
            assert "phone" not in call_json
            assert "phoneNumber" not in call_json

    @pytest.mark.asyncio
    async def test_update_message_status_not_implemented(self, conversations_client):
        """Test that update_message_status raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            await conversations_client.update_message_status("msg123", "read", "loc123")

        assert "custom conversation providers" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_messages_filters_non_dict_items(self, conversations_client):
        """Test that get_messages filters out non-dict items from messages array."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "messages": [
                {"id": "msg1", "conversationId": "conv123", "type": 1, "body": "Valid message"},
                None,  # Invalid item
                "string_item",  # Invalid item
                {"id": "msg2", "conversationId": "conv123", "type": 1, "body": "Another valid"}
            ]
        }

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await conversations_client.get_messages("conv123", "loc123")

            # Should only include valid dict items
            assert len(result.messages) == 2
            assert all(isinstance(msg, Message) for msg in result.messages)

    @pytest.mark.asyncio
    async def test_get_conversations_empty_response(self, conversations_client):
        """Test handling empty conversations response."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # Empty response

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await conversations_client.get_conversations("loc123")

            # Should handle gracefully
            assert isinstance(result, ConversationList)
            assert result.conversations == []
            assert result.count == 0
            assert result.total is None

    @pytest.mark.asyncio
    async def test_send_message_fallback_id(self, conversations_client):
        """Test send_message handles missing messageId in response."""
        message = MessageCreate(
            type=MessageType.SMS,
            conversationId="conv123",
            contactId="contact123",
            message="Test"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "conversationId": "conv123",
            "id": "msg128"  # Some APIs return 'id' instead of 'messageId'
        }

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await conversations_client.send_message("conv123", message, "loc123")

            assert result.id == "msg128"

    @pytest.mark.asyncio
    async def test_send_message_no_id_fallback(self, conversations_client):
        """Test send_message with no ID in response."""
        message = MessageCreate(
            type=MessageType.SMS,
            conversationId="conv123",
            contactId="contact123",
            message="Test"
        )

        mock_response = Mock()
        mock_response.json.return_value = {"conversationId": "conv123"}  # No ID field

        with patch.object(conversations_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await conversations_client.send_message("conv123", message, "loc123")

            assert result.id == "unknown"  # Fallback value