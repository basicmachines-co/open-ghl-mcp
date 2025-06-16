#!/usr/bin/env python3
"""
Remote MCP Server for Claude.ai Integration
Provides HTTP/SSE transport for MCP protocol alongside existing stdio server
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncIterator, List, Tuple
from datetime import datetime
from pathlib import Path
import inspect

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sse_starlette.sse import EventSourceResponse
import uvicorn

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import existing services
from src.services.oauth import OAuthService, OAuthSettings, AuthMode
from src.api.client import GoHighLevelClient
from src.utils.auth_middleware import mcp_auth, token_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GoHighLevel Remote MCP Server",
    description="Remote MCP server for Claude.ai integration with GoHighLevel",
    version="1.0.0"
)

# Add CORS middleware for Claude.ai access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
oauth_service: Optional[OAuthService] = None
ghl_clients: Dict[str, GoHighLevelClient] = {}

# Security
security = HTTPBearer()


async def get_ghl_client(location_id: str, token: str) -> GoHighLevelClient:
    """Get or create a GoHighLevel client for the given location and token"""
    cache_key = f"{location_id}:{token[:10]}"  # Use token prefix for caching
    
    if cache_key not in ghl_clients:
        # For Standard mode with remote access, we'll create a client that uses the token
        class RemoteOAuthService:
            def __init__(self, token: str, location_id: str):
                self.token = token
                self.location_id = location_id
                self.settings = OAuthSettings()
                self.settings.auth_mode = AuthMode.STANDARD
            
            async def get_location_token(self, loc_id: str) -> str:
                # Use token manager to get location-specific token
                return await token_manager.get_location_token(self.token, loc_id)
        
        # Create OAuth service wrapper
        remote_oauth = RemoteOAuthService(token, location_id)
        
        # Create GHL client
        ghl_clients[cache_key] = GoHighLevelClient(remote_oauth)
    
    return ghl_clients[cache_key]


class MCPToolRegistry:
    """Registry for MCP tools that can be called via HTTP"""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, func: Any, description: str, params_schema: Dict):
        """Register a tool"""
        self.tools[name] = {
            "func": func,
            "description": description,
            "params_schema": params_schema
        }
    
    async def call_tool(self, name: str, params: Dict, location_id: str, token: str) -> Any:
        """Call a registered tool"""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")
        
        tool = self.tools[name]
        func = tool["func"]
        
        # Get GHL client
        client = await get_ghl_client(location_id, token)
        
        # Call the tool function with client and params
        return await func(client, params, location_id)


# Create tool registry
tool_registry = MCPToolRegistry()


# Tool implementations
async def search_contacts_impl(client: GoHighLevelClient, params: Dict, location_id: str) -> Dict:
    """Search contacts implementation"""
    contacts = await client.search_contacts(
        location_id=location_id,
        query=params.get("query"),
        limit=params.get("limit", 100),
        skip=params.get("skip", 0)
    )
    return {"contacts": [c.model_dump() for c in contacts]}


async def get_contact_impl(client: GoHighLevelClient, params: Dict, location_id: str) -> Dict:
    """Get contact implementation"""
    contact = await client.get_contact(
        contact_id=params["contact_id"],
        location_id=location_id
    )
    return {"contact": contact.model_dump()}


async def create_contact_impl(client: GoHighLevelClient, params: Dict, location_id: str) -> Dict:
    """Create contact implementation"""
    from src.models.contact import ContactCreate
    
    contact_data = ContactCreate(
        locationId=location_id,
        firstName=params.get("first_name"),
        lastName=params.get("last_name"),
        email=params.get("email"),
        phone=params.get("phone"),
        tags=params.get("tags", []),
        source=params.get("source"),
        companyName=params.get("company_name"),
        address1=params.get("address"),
        city=params.get("city"),
        state=params.get("state"),
        postalCode=params.get("postal_code"),
        customFields=[
            {"key": k, "value": v} for k, v in (params.get("custom_fields", {})).items()
        ] if params.get("custom_fields") else None,
    )
    
    contact = await client.create_contact(contact_data)
    return {"success": True, "contact": contact.model_dump()}


async def send_message_impl(client: GoHighLevelClient, params: Dict, location_id: str) -> Dict:
    """Send message implementation"""
    from src.models.conversation import MessageCreate
    
    message_data = MessageCreate(
        type=params["type"],
        conversationId=params["conversation_id"],
        message=params.get("message"),
        html=params.get("html"),
        subject=params.get("subject"),
        text=params.get("text"),
        attachments=params.get("attachments", []),
        emailFrom=params.get("email_from"),
        emailTo=params.get("email_to"),
        emailCc=params.get("email_cc"),
        emailBcc=params.get("email_bcc")
    )
    
    result = await client.send_message(message_data, location_id)
    return {"success": True, "conversationId": result["conversationId"], "messageId": result["messageId"]}


async def get_conversations_impl(client: GoHighLevelClient, params: Dict, location_id: str) -> Dict:
    """Get conversations implementation"""
    conversations = await client.get_conversations(
        location_id=location_id,
        contact_id=params.get("contact_id"),
        assigned_to=params.get("assigned_to"),
        limit=params.get("limit", 20),
        offset=params.get("offset", 0)
    )
    return {"conversations": [c.model_dump() for c in conversations]}


async def search_opportunities_impl(client: GoHighLevelClient, params: Dict, location_id: str) -> Dict:
    """Search opportunities implementation"""
    opportunities = await client.search_opportunities(
        location_id=location_id,
        pipeline_id=params.get("pipeline_id"),
        pipeline_stage_id=params.get("pipeline_stage_id"),
        contact_id=params.get("contact_id"),
        status=params.get("status"),
        query=params.get("query"),
        limit=params.get("limit", 100),
        offset=params.get("offset", 0)
    )
    return {"opportunities": [o.model_dump() for o in opportunities]}


async def get_calendars_impl(client: GoHighLevelClient, params: Dict, location_id: str) -> Dict:
    """Get calendars implementation"""
    calendars = await client.get_calendars(location_id)
    return {"calendars": [c.model_dump() for c in calendars]}


async def get_free_slots_impl(client: GoHighLevelClient, params: Dict, location_id: str) -> Dict:
    """Get free slots implementation"""
    slots = await client.get_free_slots(
        calendar_id=params["calendar_id"],
        start_date=datetime.fromisoformat(params["start_date"]),
        end_date=datetime.fromisoformat(params["end_date"]),
        timezone=params["timezone"],
        location_id=location_id
    )
    return {"slots": [s.model_dump() for s in slots]}


# Register tools on startup
@app.on_event("startup")
async def startup_event():
    """Initialize OAuth service and register tools"""
    global oauth_service
    
    logger.info("Initializing HTTP MCP server...")
    
    # Initialize OAuth service
    try:
        oauth_service = OAuthService()
        logger.info(f"OAuth service initialized in {oauth_service.settings.auth_mode} mode")
    except Exception as e:
        logger.error(f"Failed to initialize OAuth service: {str(e)}")
    
    # Register tools
    tool_registry.register(
        "search_contacts",
        search_contacts_impl,
        "Search for contacts in GoHighLevel",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Number of results to return"},
                "skip": {"type": "integer", "description": "Number of results to skip"}
            }
        }
    )
    
    tool_registry.register(
        "get_contact",
        get_contact_impl,
        "Get a specific contact by ID",
        {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string", "description": "Contact ID"}
            },
            "required": ["contact_id"]
        }
    )
    
    tool_registry.register(
        "create_contact",
        create_contact_impl,
        "Create a new contact",
        {
            "type": "object",
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string"},
                "company_name": {"type": "string"},
                "address": {"type": "string"},
                "city": {"type": "string"},
                "state": {"type": "string"},
                "postal_code": {"type": "string"},
                "custom_fields": {"type": "object"}
            }
        }
    )
    
    tool_registry.register(
        "send_message",
        send_message_impl,
        "Send a message in a conversation",
        {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["SMS", "Email", "WhatsApp", "FB", "IG"]},
                "conversation_id": {"type": "string"},
                "message": {"type": "string"},
                "html": {"type": "string"},
                "subject": {"type": "string"},
                "text": {"type": "string"},
                "attachments": {"type": "array", "items": {"type": "string"}},
                "email_from": {"type": "string"},
                "email_to": {"type": "string"},
                "email_cc": {"type": "string"},
                "email_bcc": {"type": "string"}
            },
            "required": ["type", "conversation_id"]
        }
    )
    
    tool_registry.register(
        "get_conversations",
        get_conversations_impl,
        "Get conversations",
        {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string"},
                "assigned_to": {"type": "string"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"}
            }
        }
    )
    
    tool_registry.register(
        "search_opportunities",
        search_opportunities_impl,
        "Search opportunities",
        {
            "type": "object",
            "properties": {
                "pipeline_id": {"type": "string"},
                "pipeline_stage_id": {"type": "string"},
                "contact_id": {"type": "string"},
                "status": {"type": "string", "enum": ["open", "won", "lost", "abandoned"]},
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"}
            }
        }
    )
    
    tool_registry.register(
        "get_calendars",
        get_calendars_impl,
        "Get all calendars for a location",
        {
            "type": "object",
            "properties": {}
        }
    )
    
    tool_registry.register(
        "get_free_slots",
        get_free_slots_impl,
        "Get available time slots for a calendar",
        {
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string"},
                "start_date": {"type": "string", "format": "date-time"},
                "end_date": {"type": "string", "format": "date-time"},
                "timezone": {"type": "string"}
            },
            "required": ["calendar_id", "start_date", "end_date", "timezone"]
        }
    )
    
    logger.info(f"Registered {len(tool_registry.tools)} MCP tools")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return JSONResponse({
        "status": "healthy",
        "service": "GoHighLevel MCP Server",
        "timestamp": datetime.utcnow().isoformat(),
        "tools_loaded": len(tool_registry.tools)
    })


# OAuth discovery endpoint
@app.get("/.well-known/oauth-authorization-server")
async def oauth_discovery():
    """OAuth 2.1 discovery metadata"""
    base_url = os.getenv("SERVER_URL", "http://localhost:8000")
    return JSONResponse({
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "registration_endpoint": f"{base_url}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": ["ghl.full"]
    })


# Dynamic Client Registration endpoint
@app.post("/oauth/register")
async def oauth_register(request: Request):
    """Dynamic Client Registration for Claude.ai"""
    data = await request.json()
    
    # Generate client credentials
    client_id = f"claude_{datetime.utcnow().timestamp()}"
    client_secret = os.urandom(32).hex()
    
    # TODO: Store client credentials securely
    
    return JSONResponse({
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_issued_at": int(datetime.utcnow().timestamp()),
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "redirect_uris": data.get("redirect_uris", []),
        "client_name": data.get("client_name", "Claude.ai"),
        "token_endpoint_auth_method": "client_secret_post"
    })


# OAuth authorization redirect
@app.get("/oauth/authorize")
async def oauth_authorize(
    client_id: str,
    redirect_uri: str,
    response_type: str,
    state: str,
    scope: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None
):
    """Redirect to Basic Machines OAuth flow"""
    # TODO: Validate client_id and redirect_uri
    
    # Redirect to existing Basic Machines OAuth
    basic_machines_url = "https://basicmachines.co/oauth/gohighlevel"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": response_type,
        "state": state,
        "scope": scope or "ghl.full"
    }
    
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = code_challenge_method or "S256"
    
    # Build redirect URL
    from urllib.parse import urlencode
    redirect_url = f"{basic_machines_url}?{urlencode(params)}"
    
    return JSONResponse({
        "redirect": redirect_url
    }, status_code=302, headers={"Location": redirect_url})


# OAuth token endpoint
@app.post("/oauth/token")
async def oauth_token(request: Request):
    """Token exchange endpoint"""
    # Delegate to existing Basic Machines token endpoint
    # TODO: Implement token exchange logic
    return JSONResponse({
        "access_token": "test_token",
        "token_type": "bearer",
        "expires_in": 3600,
        "refresh_token": "test_refresh_token"
    })


# MCP Protocol Handler
class MCPProtocolHandler:
    """Handles MCP protocol messages over HTTP/SSE transport"""
    
    async def handle_initialize(self, params: Dict) -> Dict:
        """Handle MCP initialize request"""
        return {
            "protocolVersion": "0.1.0",
            "serverInfo": {
                "name": "GoHighLevel MCP Server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {
                    "listTools": {},
                    "callTool": {}
                }
            }
        }
    
    async def handle_tools_list(self, params: Dict) -> Dict:
        """List all available MCP tools"""
        tools_list = []
        for name, tool in tool_registry.tools.items():
            tools_list.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["params_schema"]
            })
        return {"tools": tools_list}
    
    async def handle_tools_call(self, params: Dict, location_id: str, token: str) -> Dict:
        """Execute a specific tool"""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if tool_name not in tool_registry.tools:
            raise ValueError(f"Tool {tool_name} not found")
        
        try:
            # Call tool
            result = await tool_registry.call_tool(tool_name, tool_args, location_id, token)
            
            # Format response
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return {
                "error": {
                    "code": "TOOL_ERROR",
                    "message": str(e)
                }
            }
    
    async def process_message(self, message: Dict, location_id: str, token: str) -> Dict:
        """Route MCP messages to appropriate handlers"""
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")
        
        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_tools_list(params)
            elif method == "tools/call":
                result = await self.handle_tools_call(params, location_id, token)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result
            }
        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }


# MCP Server-Sent Events endpoint
@app.get("/sse")
async def mcp_sse(auth_data: Tuple[str, str] = Depends(mcp_auth)):
    """Main MCP Server-Sent Events endpoint"""
    location_id, token = auth_data
    
    async def event_generator():
        """Generate SSE events for MCP protocol"""
        handler = MCPProtocolHandler()
        
        # Send initial connection event
        yield {
            "event": "connection",
            "data": json.dumps({
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat(),
                "location_id": location_id
            })
        }
        
        # TODO: Implement actual message queue for bidirectional communication
        # For now, this is a placeholder for the SSE stream
        
        try:
            while True:
                # In production, this would read from a message queue
                await asyncio.sleep(30)  # Keep connection alive
                yield {
                    "event": "ping",
                    "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})
                }
        except asyncio.CancelledError:
            logger.info("SSE connection closed")
    
    return EventSourceResponse(event_generator())


# Debug endpoints (remove in production)
@app.get("/debug/tools")
async def debug_tools():
    """List all loaded tools for debugging"""
    return JSONResponse({
        "tools": list(tool_registry.tools.keys()),
        "count": len(tool_registry.tools),
        "details": {
            name: {
                "description": tool["description"],
                "schema": tool["params_schema"]
            }
            for name, tool in tool_registry.tools.items()
        }
    })


@app.get("/debug/config")
async def debug_config():
    """Show current configuration for debugging"""
    return JSONResponse({
        "auth_mode": str(oauth_service.settings.auth_mode) if oauth_service else "not_initialized",
        "server_url": os.getenv("SERVER_URL", "not_set"),
        "supabase_url": os.getenv("SUPABASE_URL", "not_set"),
        "tool_count": len(tool_registry.tools)
    })


# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "http_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )