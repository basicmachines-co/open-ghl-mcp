"""Conversation tools for GoHighLevel MCP integration"""

from typing import Dict, Any

from ...models.conversation import ConversationCreate, MessageCreate, MessageType
from ..params.conversations import (
    GetConversationsParams,
    GetConversationParams,
    CreateConversationParams,
    GetMessagesParams,
    SendMessageParams,
    UpdateMessageStatusParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None


def _register_conversation_tools(_mcp, _get_client):
    """Register conversation tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    @mcp.tool()
    async def get_conversations(params: GetConversationsParams) -> Dict[str, Any]:
        """Get conversations for a location"""
        client = await get_client(params.access_token)

        result = await client.get_conversations(
            location_id=params.location_id,
            limit=params.limit,
            skip=params.skip,
            contact_id=params.contact_id,
            starred=params.starred,
            unread_only=params.unread_only,
        )

        return {
            "success": True,
            "conversations": [c.model_dump() for c in result.conversations],
            "count": result.count,
            "total": result.total,
        }

    @mcp.tool()
    async def get_conversation(params: GetConversationParams) -> Dict[str, Any]:
        """Get a single conversation"""
        client = await get_client(params.access_token)

        conversation = await client.get_conversation(
            params.conversation_id, params.location_id
        )
        return {"success": True, "conversation": conversation.model_dump()}

    @mcp.tool()
    async def create_conversation(params: CreateConversationParams) -> Dict[str, Any]:
        """Create a new conversation"""
        client = await get_client(params.access_token)

        conversation_data = ConversationCreate(
            locationId=params.location_id,
            contactId=params.contact_id,
            lastMessageType=(
                MessageType(params.message_type) if params.message_type else None
            ),
        )

        conversation = await client.create_conversation(conversation_data)
        return {"success": True, "conversation": conversation.model_dump()}

    @mcp.tool()
    async def get_messages(params: GetMessagesParams) -> Dict[str, Any]:
        """Get messages from a conversation"""
        client = await get_client(params.access_token)

        result = await client.get_messages(
            conversation_id=params.conversation_id,
            location_id=params.location_id,
            limit=params.limit,
            skip=params.skip,
        )

        return {
            "success": True,
            "messages": [m.model_dump() for m in result.messages],
            "count": result.count,
            "total": result.total,
        }

    @mcp.tool()
    async def send_message(params: SendMessageParams) -> Dict[str, Any]:
        """Send a message in a conversation"""
        client = await get_client(params.access_token)

        message_data = MessageCreate(
            type=params.message_type,
            contactId=params.contact_id,
            message=params.message,
            phone=params.phone,
            html=params.html,
            text=params.text,
            subject=params.subject,
            attachments=params.attachments,
        )

        message = await client.send_message(
            conversation_id=params.conversation_id,
            message=message_data,
            location_id=params.location_id,
        )

        return {"success": True, "message": message.model_dump()}

    @mcp.tool()
    async def update_message_status(
        params: UpdateMessageStatusParams,
    ) -> Dict[str, Any]:
        """Update the status of a message

        NOTE: This is only supported for custom conversation providers (Marketplace App feature).
        Regular messages cannot have their status updated via API.
        """
        return {
            "success": False,
            "error": "Not supported",
            "message": (
                "Message status updates are only supported for custom conversation providers. "
                "This is a Marketplace App feature and not available for standard messages."
            ),
        }
