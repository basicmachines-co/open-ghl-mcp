"""Tests for the models.conversation module."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models.conversation import (
    MessageType,
    MessageStatus,
    MessageDirection,
    Message,
    MessageCreate,
    Conversation,
    ConversationCreate,
    ConversationList,
    MessageList,
    MESSAGE_TYPE_CODES,
)


class TestMessageType:
    """Test cases for MessageType enum."""

    def test_message_type_sending_types(self):
        """Test API sending message types."""
        assert MessageType.SMS.value == "SMS"
        assert MessageType.EMAIL.value == "Email"
        assert MessageType.WHATSAPP.value == "WhatsApp"
        assert MessageType.IG.value == "IG"
        assert MessageType.FB.value == "FB"
        assert MessageType.CUSTOM.value == "Custom"
        assert MessageType.LIVE_CHAT.value == "Live_Chat"

    def test_message_type_legacy_types(self):
        """Test legacy message types for reading."""
        assert MessageType.TYPE_SMS.value == "TYPE_SMS"
        assert MessageType.TYPE_EMAIL.value == "TYPE_EMAIL"
        assert MessageType.TYPE_CALL.value == "TYPE_CALL"
        assert MessageType.TYPE_WHATSAPP.value == "TYPE_WHATSAPP"
        assert MessageType.TYPE_FB_MESSENGER.value == "TYPE_FB_MESSENGER"
        assert MessageType.TYPE_INSTAGRAM.value == "TYPE_INSTAGRAM"
        assert MessageType.TYPE_WEBCHAT.value == "TYPE_WEBCHAT"
        assert MessageType.TYPE_SMS_REVIEW_REQUEST.value == "TYPE_SMS_REVIEW_REQUEST"
        assert MessageType.TYPE_VOICE_MAIL.value == "TYPE_VOICE_MAIL"
        assert MessageType.TYPE_NO_SHOW.value == "TYPE_NO_SHOW"
        assert MessageType.TYPE_ACTIVITY_OPPORTUNITY.value == "TYPE_ACTIVITY_OPPORTUNITY"
        assert MessageType.TYPE_LIVE_CHAT_INFO_MESSAGE.value == "TYPE_LIVE_CHAT_INFO_MESSAGE"

    def test_message_type_codes_mapping(self):
        """Test message type to numeric code mapping."""
        # Sending types
        assert MESSAGE_TYPE_CODES[MessageType.SMS] == 1
        assert MESSAGE_TYPE_CODES[MessageType.EMAIL] == 2
        assert MESSAGE_TYPE_CODES[MessageType.WHATSAPP] == 5
        assert MESSAGE_TYPE_CODES[MessageType.FB] == 7
        assert MESSAGE_TYPE_CODES[MessageType.IG] == 15
        assert MESSAGE_TYPE_CODES[MessageType.LIVE_CHAT] == 11
        
        # Legacy types
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_SMS] == 1
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_EMAIL] == 2
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_CALL] == 3
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_WHATSAPP] == 5
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_FB_MESSENGER] == 7
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_INSTAGRAM] == 15
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_WEBCHAT] == 11
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_SMS_REVIEW_REQUEST] == 13
        assert MESSAGE_TYPE_CODES[MessageType.TYPE_VOICE_MAIL] == 14


class TestMessageStatus:
    """Test cases for MessageStatus enum."""

    def test_message_status_values(self):
        """Test all message status values."""
        assert MessageStatus.SENT.value == "sent"
        assert MessageStatus.DELIVERED.value == "delivered"
        assert MessageStatus.READ.value == "read"
        assert MessageStatus.FAILED.value == "failed"
        assert MessageStatus.PENDING.value == "pending"
        assert MessageStatus.VOICEMAIL.value == "voicemail"


class TestMessageDirection:
    """Test cases for MessageDirection enum."""

    def test_message_direction_values(self):
        """Test message direction values."""
        assert MessageDirection.INBOUND.value == "inbound"
        assert MessageDirection.OUTBOUND.value == "outbound"


class TestMessage:
    """Test cases for Message model."""

    def test_message_minimal(self):
        """Test creating a Message with minimal required fields."""
        message = Message(
            id="msg123",
            conversationId="conv123",
            type=1  # Numeric type for SMS
        )
        
        assert message.id == "msg123"
        assert message.conversationId == "conv123"
        assert message.type == 1
        assert message.body is None
        assert message.status is None

    def test_message_with_string_type(self):
        """Test creating a Message with string MessageType."""
        message = Message(
            id="msg123",
            conversationId="conv123",
            type=MessageType.EMAIL,
            messageType=MessageType.TYPE_EMAIL,
            body="Test email"
        )
        
        assert message.type == MessageType.EMAIL
        assert message.messageType == MessageType.TYPE_EMAIL
        assert message.body == "Test email"

    def test_message_full(self):
        """Test creating a Message with all common fields."""
        now = datetime.now(timezone.utc)
        attachments = [{"url": "https://example.com/file.pdf", "name": "file.pdf"}]
        
        message = Message(
            id="msg123",
            conversationId="conv123",
            locationId="loc123",
            contactId="contact123",
            body="Test message",
            type=1,
            messageType=MessageType.TYPE_SMS,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.DELIVERED,
            dateAdded=now,
            dateUpdated=now,
            attachments=attachments,
            meta={"key": "value"},
            source="api",
            userId="user123",
            contentType="text/plain"
        )
        
        assert message.locationId == "loc123"
        assert message.direction == MessageDirection.OUTBOUND
        assert message.status == MessageStatus.DELIVERED
        assert message.dateAdded == now
        assert message.attachments == attachments
        assert message.meta == {"key": "value"}

    def test_message_flexible_status(self):
        """Test that message status accepts any string value."""
        # Standard status
        message1 = Message(
            id="msg1",
            conversationId="conv123",
            type=1,
            status=MessageStatus.SENT
        )
        assert message1.status == MessageStatus.SENT
        
        # Custom string status
        message2 = Message(
            id="msg2",
            conversationId="conv123",
            type=1,
            status="custom_status"
        )
        assert message2.status == "custom_status"

    def test_message_datetime_handling(self):
        """Test Message datetime field handling."""
        # With datetime objects
        now = datetime.now(timezone.utc)
        message1 = Message(
            id="msg1",
            conversationId="conv123",
            type=1,
            dateAdded=now,
            dateUpdated=now
        )
        assert message1.dateAdded == now
        assert message1.dateUpdated == now
        
        # With ISO strings
        iso_string = "2025-06-16T10:00:00Z"
        message2 = Message(
            id="msg2",
            conversationId="conv123",
            type=1,
            dateAdded=iso_string,
            dateUpdated=iso_string
        )
        assert message2.dateAdded == iso_string
        assert message2.dateUpdated == iso_string

    def test_message_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Message(id="msg123")  # Missing conversationId and type
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "conversationId" in error_fields
        assert "type" in error_fields


class TestMessageCreate:
    """Test cases for MessageCreate model."""

    def test_message_create_sms(self):
        """Test creating an SMS message."""
        message = MessageCreate(
            type=MessageType.SMS,
            contactId="contact123",
            message="Hello via SMS",
            phone="+1234567890"
        )
        
        assert message.type == MessageType.SMS
        assert message.contactId == "contact123"
        assert message.message == "Hello via SMS"
        assert message.phone == "+1234567890"
        assert message.html is None
        assert message.subject is None

    def test_message_create_email(self):
        """Test creating an email message."""
        message = MessageCreate(
            type=MessageType.EMAIL,
            contactId="contact123",
            html="<p>Hello via Email</p>",
            text="Hello via Email",
            subject="Test Subject"
        )
        
        assert message.type == MessageType.EMAIL
        assert message.html == "<p>Hello via Email</p>"
        assert message.text == "Hello via Email"
        assert message.subject == "Test Subject"
        assert message.message is None
        assert message.phone is None

    def test_message_create_with_numeric_type(self):
        """Test creating a message with numeric type."""
        message = MessageCreate(
            type=1,  # Numeric type for SMS
            contactId="contact123",
            message="Test"
        )
        
        assert message.type == 1
        assert message.contactId == "contact123"

    def test_message_create_with_attachments(self):
        """Test creating a message with attachments."""
        attachments = [
            {"url": "https://example.com/image.jpg", "type": "image/jpeg"},
            {"url": "https://example.com/doc.pdf", "type": "application/pdf"}
        ]
        
        message = MessageCreate(
            type=MessageType.SMS,
            contactId="contact123",
            message="See attachments",
            attachments=attachments
        )
        
        assert message.attachments == attachments
        assert len(message.attachments) == 2

    def test_message_create_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            MessageCreate(message="Hello")  # Missing type and contactId
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "type" in error_fields
        assert "contactId" in error_fields


class TestConversation:
    """Test cases for Conversation model."""

    def test_conversation_minimal(self):
        """Test creating a Conversation with minimal required fields."""
        conversation = Conversation(
            id="conv123",
            locationId="loc123",
            contactId="contact123"
        )
        
        assert conversation.id == "conv123"
        assert conversation.locationId == "loc123"
        assert conversation.contactId == "contact123"
        assert conversation.unreadCount == 0
        assert conversation.starred is False
        assert conversation.deleted is False
        assert conversation.inbox is True
        assert conversation.followers == []
        assert conversation.tags == []

    def test_conversation_full(self):
        """Test creating a Conversation with all common fields."""
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        conversation = Conversation(
            id="conv123",
            locationId="loc123",
            contactId="contact123",
            lastMessageBody="Last message",
            lastMessageType="TYPE_SMS",
            lastMessageDate=now_ms,
            lastMessageDirection="inbound",
            lastOutboundMessageAction="sent",
            lastManualMessageDate=now_ms,
            unreadCount=5,
            dateAdded=now_ms,
            dateUpdated=now_ms,
            starred=True,
            deleted=False,
            inbox=True,
            assignedTo="user123",
            userId="user456",
            followers=["user789", "user101"],
            isLastMessageInternalComment=False,
            fullName="John Doe",
            contactName="John",
            companyName="Acme Corp",
            email="john@example.com",
            phone="+1234567890",
            tags=["vip", "customer"],
            type="TYPE_PHONE",
            scoring=[{"type": "lead_score", "value": 85}],
            attributed=True,
            sort=[1, 2, 3]
        )
        
        assert conversation.lastMessageBody == "Last message"
        assert conversation.lastMessageType == "TYPE_SMS"
        assert conversation.lastMessageDate == now_ms
        assert conversation.unreadCount == 5
        assert conversation.starred is True
        assert conversation.assignedTo == "user123"
        assert len(conversation.followers) == 2
        assert conversation.tags == ["vip", "customer"]
        assert conversation.type == "TYPE_PHONE"

    def test_conversation_timestamp_fields(self):
        """Test Conversation timestamp fields as milliseconds."""
        # Unix timestamp in milliseconds
        timestamp_ms = 1750000000000  # Some future timestamp
        
        conversation = Conversation(
            id="conv123",
            locationId="loc123",
            contactId="contact123",
            lastMessageDate=timestamp_ms,
            lastManualMessageDate=timestamp_ms,
            dateAdded=timestamp_ms,
            dateUpdated=timestamp_ms
        )
        
        assert conversation.lastMessageDate == timestamp_ms
        assert conversation.lastManualMessageDate == timestamp_ms
        assert conversation.dateAdded == timestamp_ms
        assert conversation.dateUpdated == timestamp_ms

    def test_conversation_type_variants(self):
        """Test that conversation type can be string or int."""
        # String type
        conv1 = Conversation(
            id="conv1",
            locationId="loc123",
            contactId="contact123",
            type="TYPE_PHONE"
        )
        assert conv1.type == "TYPE_PHONE"
        
        # Numeric type
        conv2 = Conversation(
            id="conv2",
            locationId="loc123",
            contactId="contact123",
            type=1
        )
        assert conv2.type == 1

    def test_conversation_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Conversation(id="conv123")  # Missing locationId and contactId
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "locationId" in error_fields
        assert "contactId" in error_fields


class TestConversationCreate:
    """Test cases for ConversationCreate model."""

    def test_conversation_create_minimal(self):
        """Test creating ConversationCreate with minimal fields."""
        conv_create = ConversationCreate(
            locationId="loc123",
            contactId="contact123"
        )
        
        assert conv_create.locationId == "loc123"
        assert conv_create.contactId == "contact123"
        assert conv_create.lastMessageType is None

    def test_conversation_create_with_message_type(self):
        """Test creating ConversationCreate with message type."""
        conv_create = ConversationCreate(
            locationId="loc123",
            contactId="contact123",
            lastMessageType=MessageType.EMAIL
        )
        
        assert conv_create.lastMessageType == MessageType.EMAIL

    def test_conversation_create_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationCreate(locationId="loc123")  # Missing contactId
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "contactId" for e in errors)


class TestConversationList:
    """Test cases for ConversationList model."""

    def test_conversation_list_minimal(self):
        """Test ConversationList with minimal fields."""
        conversations = [
            Conversation(id="conv1", locationId="loc123", contactId="contact1"),
            Conversation(id="conv2", locationId="loc123", contactId="contact2")
        ]
        
        conv_list = ConversationList(
            conversations=conversations,
            count=2
        )
        
        assert len(conv_list.conversations) == 2
        assert conv_list.count == 2
        assert conv_list.total is None
        assert conv_list.traceId is None

    def test_conversation_list_full(self):
        """Test ConversationList with all fields."""
        conv_list = ConversationList(
            conversations=[],
            count=0,
            total=100,
            traceId="trace123"
        )
        
        assert conv_list.conversations == []
        assert conv_list.count == 0
        assert conv_list.total == 100
        assert conv_list.traceId == "trace123"

    def test_conversation_list_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationList(conversations=[])  # Missing count
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "count" for e in errors)


class TestMessageList:
    """Test cases for MessageList model."""

    def test_message_list_minimal(self):
        """Test MessageList with minimal fields."""
        messages = [
            Message(id="msg1", conversationId="conv123", type=1),
            Message(id="msg2", conversationId="conv123", type=2)
        ]
        
        msg_list = MessageList(
            messages=messages,
            count=2
        )
        
        assert len(msg_list.messages) == 2
        assert msg_list.count == 2
        assert msg_list.total is None

    def test_message_list_with_total(self):
        """Test MessageList with total field."""
        msg_list = MessageList(
            messages=[],
            count=0,
            total=50
        )
        
        assert msg_list.messages == []
        assert msg_list.count == 0
        assert msg_list.total == 50

    def test_message_list_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            MessageList(messages=[])  # Missing count
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "count" for e in errors)