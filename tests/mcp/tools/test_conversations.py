"""Tests for the mcp.tools.conversations module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.models.conversation import (
    Conversation, 
    ConversationList, 
    ConversationCreate,
    Message, 
    MessageList, 
    MessageCreate,
    MessageType,
    MessageStatus,
    MessageDirection
)
from src.mcp.params.conversations import (
    GetConversationsParams,
    GetConversationParams,
    CreateConversationParams,
    GetMessagesParams,
    SendMessageParams,
    UpdateMessageStatusParams,
)
from src.mcp.tools.conversations import _register_conversation_tools


class TestConversationTools:
    """Test cases for conversation tools."""

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
        """Set up conversation tools with mocks."""
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
        _register_conversation_tools(mock_mcp, get_client_func)
        
        return tools, mock_client

    @pytest.mark.asyncio
    async def test_get_conversations(self, setup_tools):
        """Test get_conversations tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        # Use Unix timestamps in milliseconds
        now_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_conversations = [
            Conversation(
                id="conv1",
                locationId="loc123",
                contactId="contact1",
                type=MessageType.SMS,
                dateAdded=now_timestamp,
                dateUpdated=now_timestamp,
                lastMessageBody="Hello",
                lastMessageDate=now_timestamp,
                lastMessageType=MessageType.SMS,
                lastMessageDirection=MessageDirection.OUTBOUND,
                unreadCount=0,
                starred=False
            ),
            Conversation(
                id="conv2",
                locationId="loc123",
                contactId="contact2",
                type=MessageType.EMAIL,
                dateAdded=now_timestamp,
                dateUpdated=now_timestamp,
                lastMessageBody="Welcome",
                lastMessageDate=now_timestamp,
                lastMessageType=MessageType.EMAIL,
                lastMessageDirection=MessageDirection.INBOUND,
                unreadCount=2,
                starred=True
            )
        ]
        mock_result = ConversationList(conversations=mock_conversations, count=2, total=10)
        mock_client.get_conversations.return_value = mock_result
        
        # Create params
        params = GetConversationsParams(
            location_id="loc123",
            limit=10,
            skip=0,
            unread_only=True,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_conversations"](params)
        
        # Verify
        assert result["success"] is True
        assert len(result["conversations"]) == 2
        assert result["count"] == 2
        assert result["total"] == 10
        assert result["conversations"][0]["id"] == "conv1"
        assert result["conversations"][1]["id"] == "conv2"
        mock_client.get_conversations.assert_called_once_with(
            location_id="loc123",
            limit=10,
            skip=0,
            contact_id=None,
            starred=None,
            unread_only=True
        )

    @pytest.mark.asyncio
    async def test_get_conversations_with_filters(self, setup_tools):
        """Test get_conversations with contact and starred filters."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_result = ConversationList(conversations=[], count=0, total=0)
        mock_client.get_conversations.return_value = mock_result
        
        # Create params with filters
        params = GetConversationsParams(
            location_id="loc123",
            contact_id="contact123",
            starred=True,
            limit=20,
            skip=10,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_conversations"](params)
        
        # Verify filters were passed
        assert result["success"] is True
        mock_client.get_conversations.assert_called_once_with(
            location_id="loc123",
            limit=20,
            skip=10,
            contact_id="contact123",
            starred=True,
            unread_only=None
        )

    @pytest.mark.asyncio
    async def test_get_conversation(self, setup_tools):
        """Test get_conversation tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        now_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_conversation = Conversation(
            id="conv123",
            locationId="loc123",
            contactId="contact123",
            type=MessageType.SMS,
            dateAdded=now_timestamp,
            dateUpdated=now_timestamp,
            lastMessageBody="Test message",
            lastMessageDate=now_timestamp,
            lastMessageType=MessageType.SMS,
            lastMessageDirection=MessageDirection.OUTBOUND,
            unreadCount=0,
            starred=False
        )
        mock_client.get_conversation.return_value = mock_conversation
        
        # Create params
        params = GetConversationParams(
            conversation_id="conv123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_conversation"](params)
        
        # Verify
        assert result["success"] is True
        assert result["conversation"]["id"] == "conv123"
        assert result["conversation"]["contactId"] == "contact123"
        mock_client.get_conversation.assert_called_once_with("conv123", "loc123")

    @pytest.mark.asyncio
    async def test_create_conversation(self, setup_tools):
        """Test create_conversation tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        now_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_conversation = Conversation(
            id="conv123",
            locationId="loc123",
            contactId="contact123",
            type=MessageType.SMS,
            dateAdded=now_timestamp,
            dateUpdated=now_timestamp,
            unreadCount=0
        )
        mock_client.create_conversation.return_value = mock_conversation
        
        # Create params
        params = CreateConversationParams(
            location_id="loc123",
            contact_id="contact123",
            message_type="SMS",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["create_conversation"](params)
        
        # Verify
        assert result["success"] is True
        assert result["conversation"]["id"] == "conv123"
        assert result["conversation"]["contactId"] == "contact123"
        
        # Verify the client was called with correct data
        create_call_args = mock_client.create_conversation.call_args[0][0]
        assert create_call_args.locationId == "loc123"
        assert create_call_args.contactId == "contact123"
        assert create_call_args.lastMessageType == MessageType.SMS

    @pytest.mark.asyncio
    async def test_create_conversation_without_message_type(self, setup_tools):
        """Test create_conversation without message type."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        now_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_conversation = Conversation(
            id="conv123",
            locationId="loc123",
            contactId="contact123",
            type=MessageType.SMS,
            dateAdded=now_timestamp,
            dateUpdated=now_timestamp
        )
        mock_client.create_conversation.return_value = mock_conversation
        
        # Create params without message_type
        params = CreateConversationParams(
            location_id="loc123",
            contact_id="contact123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["create_conversation"](params)
        
        # Verify
        assert result["success"] is True
        # Verify lastMessageType is None when not provided
        create_call_args = mock_client.create_conversation.call_args[0][0]
        assert create_call_args.lastMessageType is None

    @pytest.mark.asyncio
    async def test_get_messages(self, setup_tools):
        """Test get_messages tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_messages = [
            Message(
                id="msg1",
                conversationId="conv123",
                locationId="loc123",
                contactId="contact123",
                type=1,  # SMS
                messageType="TYPE_SMS",
                direction=MessageDirection.OUTBOUND,
                status=MessageStatus.DELIVERED,
                body="Hello there",
                dateAdded=datetime.now(timezone.utc)
            ),
            Message(
                id="msg2",
                conversationId="conv123",
                locationId="loc123",
                contactId="contact123",
                type=2,  # Email
                messageType="TYPE_EMAIL",
                direction=MessageDirection.INBOUND,
                status=MessageStatus.SENT,
                body="Reply message",
                dateAdded=datetime.now(timezone.utc)
            )
        ]
        mock_result = MessageList(messages=mock_messages, count=2, total=5)
        mock_client.get_messages.return_value = mock_result
        
        # Create params
        params = GetMessagesParams(
            conversation_id="conv123",
            location_id="loc123",
            limit=10,
            skip=0,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_messages"](params)
        
        # Verify
        assert result["success"] is True
        assert len(result["messages"]) == 2
        assert result["count"] == 2
        assert result["total"] == 5
        assert result["messages"][0]["id"] == "msg1"
        assert result["messages"][0]["body"] == "Hello there"
        mock_client.get_messages.assert_called_once_with(
            conversation_id="conv123",
            location_id="loc123",
            limit=10,
            skip=0
        )

    @pytest.mark.asyncio
    async def test_send_message_sms(self, setup_tools):
        """Test send_message tool for SMS."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_response = Message(
            id="msg123",
            conversationId="conv123",
            body="Test SMS message",
            type=1,  # SMS
            contactId="contact123",
            status="sent"
        )
        mock_client.send_message.return_value = mock_response
        
        # Create params
        params = SendMessageParams(
            conversation_id="conv123",
            location_id="loc123",
            contact_id="contact123",
            message_type="SMS",
            message="Test SMS message",
            phone="+1234567890",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["send_message"](params)
        
        # Verify
        assert result["success"] is True
        assert result["message"]["conversationId"] == "conv123"
        assert result["message"]["id"] == "msg123"
        
        # Verify the client was called with correct data
        call_args = mock_client.send_message.call_args
        assert call_args[1]["conversation_id"] == "conv123"
        assert call_args[1]["location_id"] == "loc123"
        
        message_data = call_args[1]["message"]
        assert message_data.type == "SMS"
        assert message_data.message == "Test SMS message"
        assert message_data.phone == "+1234567890"
        assert message_data.contactId == "contact123"

    @pytest.mark.asyncio
    async def test_send_message_email(self, setup_tools):
        """Test send_message tool for Email."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_response = Message(
            id="msg123",
            conversationId="conv123",
            body="Test email",
            type=2,  # Email
            contactId="contact123",
            status="sent"
        )
        mock_client.send_message.return_value = mock_response
        
        # Create params
        params = SendMessageParams(
            conversation_id="conv123",
            location_id="loc123",
            contact_id="contact123",
            message_type="Email",
            html="<p>Test email</p>",
            text="Test email",
            subject="Test Subject",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["send_message"](params)
        
        # Verify
        assert result["success"] is True
        
        # Verify the client was called with correct data
        call_args = mock_client.send_message.call_args
        message_data = call_args[1]["message"]
        assert message_data.type == "Email"
        assert message_data.html == "<p>Test email</p>"
        assert message_data.text == "Test email"
        assert message_data.subject == "Test Subject"
        assert message_data.message is None  # Email doesn't use message field

    @pytest.mark.asyncio
    async def test_send_message_with_attachments(self, setup_tools):
        """Test send_message with attachments."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_response = Message(
            id="msg123",
            conversationId="conv123",
            body="Check this attachment",
            type=1,  # SMS
            contactId="contact123",
            status="sent"
        )
        mock_client.send_message.return_value = mock_response
        
        # Create params with attachments
        params = SendMessageParams(
            conversation_id="conv123",
            location_id="loc123",
            contact_id="contact123",
            message_type="SMS",
            message="Check this attachment",
            phone="+1234567890",
            attachments=[{"url": "https://example.com/file.pdf", "name": "file.pdf"}],
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["send_message"](params)
        
        # Verify
        assert result["success"] is True
        
        # Verify attachments were passed
        call_args = mock_client.send_message.call_args
        message_data = call_args[1]["message"]
        assert message_data.attachments == [{"url": "https://example.com/file.pdf", "name": "file.pdf"}]

    @pytest.mark.asyncio
    async def test_update_message_status(self, setup_tools):
        """Test update_message_status tool (not supported)."""
        tools, mock_client = setup_tools
        
        # Create params
        params = UpdateMessageStatusParams(
            message_id="msg123",
            location_id="loc123",
            status="read",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["update_message_status"](params)
        
        # Verify it returns not supported
        assert result["success"] is False
        assert result["error"] == "Not supported"
        assert "custom conversation providers" in result["message"]
        
        # Verify client was not called
        mock_client.update_message_status.assert_not_called()