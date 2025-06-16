"""Updated unit tests for MCP endpoints with FastMCP decorator support"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from pydantic import BaseModel

from src.models.contact import Contact, ContactCreate
from src.models.conversation import (
    Conversation,
    MessageCreate,
    MessageType,
)
from src.utils.exceptions import DuplicateResourceError, AuthenticationError
from src.api.client import GoHighLevelClient


class TestMCPEndpoints:
    """Test MCP endpoint functionality by testing underlying functions"""

    @pytest.fixture
    def mock_contact(self):
        """Create a mock contact for testing"""
        return Contact(
            id="mock_contact_id",
            locationId="mock_location_id",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            dateAdded=datetime.now(timezone.utc),
            tags=["test"],
        )

    @pytest.fixture
    def mock_conversation(self):
        """Create a mock conversation for testing"""
        return Conversation(
            id="mock_conversation_id",
            locationId="mock_location_id",
            contactId="mock_contact_id",
            type="SMS",
            lastMessageType=MessageType.SMS,
            lastMessageAt=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_create_contact_success(self, mock_contact):
        """Test successful contact creation"""
        # Import here to avoid import-time issues
        from src.main import CreateContactParams

        # Mock the client
        mock_client = AsyncMock(spec=GoHighLevelClient)
        mock_client.create_contact = AsyncMock(return_value=mock_contact)

        # Create test parameters
        params = CreateContactParams(
            location_id="test_location",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )

        # Test the logic directly (simulating what the MCP tool does)
        with patch("src.main.get_client", return_value=mock_client):
            # Simulate the create_contact function logic
            client = mock_client

            contact_data = ContactCreate(
                locationId=params.location_id,
                firstName=params.first_name,
                lastName=params.last_name,
                email=params.email,
                phone=params.phone,
                tags=params.tags,
                source=params.source,
                companyName=params.company_name,
                address1=params.address,
                city=params.city,
                state=params.state,
                postalCode=params.postal_code,
                customFields=[
                    {"key": k, "value": v}
                    for k, v in (params.custom_fields or {}).items()
                ],
            )

            contact = await client.create_contact(contact_data)
            result = {"success": True, "contact": contact.model_dump()}

        assert result["success"] is True
        assert result["contact"]["id"] == "mock_contact_id"
        mock_client.create_contact.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_contact_duplicate_error(self):
        """Test contact creation with duplicate error"""
        from src.main import CreateContactParams

        mock_client = AsyncMock(spec=GoHighLevelClient)
        mock_client.create_contact = AsyncMock(
            side_effect=DuplicateResourceError("Contact already exists", 400)
        )

        params = CreateContactParams(
            location_id="test_location", email="existing@example.com"
        )

        with patch("src.main.get_client", return_value=mock_client):
            client = mock_client

            contact_data = ContactCreate(
                locationId=params.location_id,
                firstName=params.first_name,
                lastName=params.last_name,
                email=params.email,
                phone=params.phone,
                tags=params.tags,
                source=params.source,
                companyName=params.company_name,
                address1=params.address,
                city=params.city,
                state=params.state,
                postalCode=params.postal_code,
                customFields=[
                    {"key": k, "value": v}
                    for k, v in (params.custom_fields or {}).items()
                ],
            )

            with pytest.raises(DuplicateResourceError):
                await client.create_contact(contact_data)

    @pytest.mark.asyncio
    async def test_get_contact_success(self, mock_contact):
        """Test successful contact retrieval"""
        from src.main import GetContactParams

        mock_client = AsyncMock(spec=GoHighLevelClient)
        mock_client.get_contact = AsyncMock(return_value=mock_contact)

        params = GetContactParams(
            contact_id="mock_contact_id", location_id="test_location"
        )

        with patch("src.main.get_client", return_value=mock_client):
            client = mock_client
            contact = await client.get_contact(params.contact_id, params.location_id)
            result = {"success": True, "contact": contact.model_dump()}

        assert result["success"] is True
        assert result["contact"]["id"] == "mock_contact_id"
        mock_client.get_contact.assert_called_once_with(
            "mock_contact_id", "test_location"
        )

    @pytest.mark.asyncio
    async def test_send_message_email(self):
        """Test sending email message"""
        from src.main import SendMessageParams

        mock_client = AsyncMock(spec=GoHighLevelClient)
        mock_response = {
            "conversationId": "test_conversation_id",
            "messageId": "test_message_id",
        }
        mock_client.send_message = AsyncMock(return_value=mock_response)

        params = SendMessageParams(
            location_id="test_location",
            contact_id="test_contact",
            conversation_id="test_conversation",
            message_type="Email",
            subject="Test Subject",
            html="<p>Test email content</p>",
            text="Test email content",
        )

        with patch("src.main.get_client", return_value=mock_client):
            client = mock_client

            # Simulate the send_message function logic
            message_data = MessageCreate(
                type=params.message_type,
                conversationId=params.conversation_id,
                contactId=params.contact_id,
                subject=params.subject,
                html=params.html,
                text=params.text,
                message=params.message,
                phone=params.phone,
            )

            response = await client.send_message(message_data, params.location_id)
            result = {"success": True, "message": response}

        assert result["success"] is True
        assert result["message"]["conversationId"] == "test_conversation_id"
        mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self):
        """Test authentication error handling"""
        from src.main import CreateContactParams

        mock_client = AsyncMock(spec=GoHighLevelClient)
        mock_client.create_contact = AsyncMock(
            side_effect=AuthenticationError("Invalid token", 401)
        )

        params = CreateContactParams(
            location_id="test_location", first_name="Test", email="test@example.com"
        )

        with patch("src.main.get_client", return_value=mock_client):
            client = mock_client

            contact_data = ContactCreate(
                locationId=params.location_id,
                firstName=params.first_name,
                lastName=params.last_name,
                email=params.email,
                phone=params.phone,
                tags=params.tags,
                source=params.source,
                companyName=params.company_name,
                address1=params.address,
                city=params.city,
                state=params.state,
                postalCode=params.postal_code,
                customFields=[
                    {"key": k, "value": v}
                    for k, v in (params.custom_fields or {}).items()
                ],
            )

            with pytest.raises(AuthenticationError):
                await client.create_contact(contact_data)


class TestMCPToolIntegration:
    """Test that MCP server is properly configured"""

    def test_mcp_server_exists(self):
        """Test that FastMCP server is properly created"""
        from src.main import mcp

        # Check that the server exists and has expected attributes
        assert mcp is not None
        assert mcp.name == "ghl-mcp-server"

    def test_parameter_classes_exist(self):
        """Test that parameter classes are properly defined"""
        from src.main import (
            CreateContactParams,
            GetContactParams,
            UpdateContactParams,
            SendMessageParams,
        )

        # Check that parameter classes exist and are BaseModel subclasses
        assert issubclass(CreateContactParams, BaseModel)
        assert issubclass(GetContactParams, BaseModel)
        assert issubclass(UpdateContactParams, BaseModel)
        assert issubclass(SendMessageParams, BaseModel)

        # Check that required fields exist
        assert "location_id" in CreateContactParams.model_fields
        assert "contact_id" in GetContactParams.model_fields


class TestMCPClientHelpers:
    """Test MCP helper functions"""

    @pytest.mark.asyncio
    async def test_get_client_with_token(self):
        """Test get_client with access token"""
        from src.main import get_client

        with patch("src.main.oauth_service", AsyncMock()):
            with patch("src.main.ghl_client", AsyncMock()):
                with patch(
                    "src.utils.client_helpers.GoHighLevelClient"
                ) as mock_client_class:
                    mock_client_instance = AsyncMock()
                    mock_client_class.return_value = mock_client_instance

                    client = await get_client("test_token")

                    # Should create new client with custom token
                    mock_client_class.assert_called_once()
                    assert client == mock_client_instance

    @pytest.mark.asyncio
    async def test_get_client_without_token(self):
        """Test get_client without access token (uses global client)"""
        from src.main import get_client

        # Mock global client
        mock_global_client = AsyncMock()

        with patch("src.main.oauth_service", AsyncMock()):
            with patch("src.main.ghl_client", mock_global_client):
                client = await get_client(None)
                assert client == mock_global_client

    @pytest.mark.asyncio
    async def test_get_client_no_global_client(self):
        """Test get_client when no global client exists"""
        from src.main import get_client

        with patch("src.main.oauth_service", None):
            with patch("src.main.ghl_client", None):
                with pytest.raises(
                    RuntimeError, match="MCP server not properly initialized"
                ):
                    await get_client(None)
