"""Opportunity tools for GoHighLevel MCP integration"""

import sys
from typing import Dict, Any
from pathlib import Path

from ...models.opportunity import (
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityStatus,
    OpportunitySearchFilters,
)
from ..params.opportunities import (
    GetOpportunitiesParams,
    GetOpportunityParams,
    CreateOpportunityParams,
    UpdateOpportunityParams,
    DeleteOpportunityParams,
    UpdateOpportunityStatusParams,
    GetPipelinesParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None
oauth_service = None


def _register_opportunity_tools(_mcp, _get_client, _oauth_service):
    """Register opportunity tools with the MCP instance"""
    global mcp, get_client, oauth_service
    mcp = _mcp
    get_client = _get_client
    oauth_service = _oauth_service

    @mcp.tool()
    async def get_opportunities(params: GetOpportunitiesParams) -> Dict[str, Any]:
        """Get opportunities for a location"""
        client = await get_client(params.access_token)

        # Build filters
        filters = OpportunitySearchFilters(
            pipelineId=params.pipeline_id,
            pipelineStageId=params.pipeline_stage_id,
            assignedTo=params.assigned_to,
            status=params.status,
            contactId=params.contact_id,
            startDate=None,
            endDate=None,
            query=params.query,
        )

        result = await client.get_opportunities(
            location_id=params.location_id,
            limit=params.limit,
            skip=params.skip,
            filters=filters,
        )

        return {
            "success": True,
            "opportunities": [o.model_dump() for o in result.opportunities],
            "count": result.count,
            "total": result.total,
        }

    @mcp.tool()
    async def get_opportunity(params: GetOpportunityParams) -> Dict[str, Any]:
        """Get a single opportunity by ID"""
        client = await get_client(params.access_token)

        opportunity = await client.get_opportunity(
            params.opportunity_id, params.location_id
        )
        return {"success": True, "opportunity": opportunity.model_dump()}

    @mcp.tool()
    async def create_opportunity(params: CreateOpportunityParams) -> Dict[str, Any]:
        """Create a new opportunity in GoHighLevel"""
        client = await get_client(params.access_token)

        opportunity_data = OpportunityCreate(
            pipelineId=params.pipeline_id,
            locationId=params.location_id,
            name=params.name,
            pipelineStageId=params.pipeline_stage_id,
            status=params.status or OpportunityStatus.OPEN,
            contactId=params.contact_id,
            monetaryValue=params.monetary_value,
            assignedTo=params.assigned_to,
            source=params.source,
            customFields=(
                [
                    {"key": k, "value": v}
                    for k, v in (params.custom_fields or {}).items()
                ]
                if params.custom_fields
                else None
            ),
        )

        opportunity = await client.create_opportunity(opportunity_data)
        return {"success": True, "opportunity": opportunity.model_dump()}

    @mcp.tool()
    async def update_opportunity(params: UpdateOpportunityParams) -> Dict[str, Any]:
        """Update an existing opportunity in GoHighLevel"""
        client = await get_client(params.access_token)

        update_data = OpportunityUpdate(
            name=params.name,
            pipelineStageId=params.pipeline_stage_id,
            status=params.status,
            monetaryValue=params.monetary_value,
            assignedTo=params.assigned_to,
            source=params.source,
            customFields=(
                [
                    {"key": k, "value": v}
                    for k, v in (params.custom_fields or {}).items()
                ]
                if params.custom_fields
                else None
            ),
        )

        opportunity = await client.update_opportunity(
            params.opportunity_id, update_data, params.location_id
        )
        return {"success": True, "opportunity": opportunity.model_dump()}

    @mcp.tool()
    async def delete_opportunity(params: DeleteOpportunityParams) -> Dict[str, Any]:
        """Delete an opportunity from GoHighLevel"""
        client = await get_client(params.access_token)

        success = await client.delete_opportunity(
            params.opportunity_id, params.location_id
        )
        return {
            "success": success,
            "message": (
                "Opportunity deleted successfully"
                if success
                else "Failed to delete opportunity"
            ),
        }

    @mcp.tool()
    async def update_opportunity_status(
        params: UpdateOpportunityStatusParams,
    ) -> Dict[str, Any]:
        """Update the status of an opportunity"""
        client = await get_client(params.access_token)

        opportunity = await client.update_opportunity_status(
            opportunity_id=params.opportunity_id,
            status=params.status,
            location_id=params.location_id,
        )

        return {"success": True, "opportunity": opportunity.model_dump()}

    @mcp.tool()
    async def get_pipelines(params: GetPipelinesParams) -> Dict[str, Any]:
        """Get all pipelines for a location

        NOTE: This is the only pipeline endpoint that exists in the API.
        Individual pipeline and stage endpoints do not exist.
        Stages are included in each pipeline object.
        """
        client = await get_client(params.access_token)

        pipelines = await client.get_pipelines(params.location_id)
        return {
            "success": True,
            "pipelines": [p.model_dump() for p in pipelines],
            "count": len(pipelines),
        }

    @mcp.tool()
    async def debug_config() -> Dict[str, Any]:
        """Debug tool to show current MCP server configuration and auth status"""
        import os

        if oauth_service is None:
            return {"error": "OAuth service not initialized"}

        # Use absolute paths based on module location
        project_root = Path(__file__).parent.parent.parent.parent
        cwd = Path.cwd()
        env_file = project_root / ".env"
        tokens_file = project_root / "config" / "tokens.json"
        standard_config_file = project_root / "config" / "standard_config.json"

        # Check token validity
        token_status = "unknown"
        token_expires_at = None
        if tokens_file.exists():
            try:
                import json
                from datetime import datetime

                with open(tokens_file) as f:
                    token_data = json.load(f)
                expires_at = datetime.fromisoformat(
                    token_data["expires_at"].replace("Z", "+00:00")
                )
                now = datetime.now(expires_at.tzinfo)
                token_status = "valid" if expires_at > now else "expired"
                token_expires_at = token_data["expires_at"]
            except Exception as e:
                token_status = f"error: {e}"

        return {
            "environment": {
                "working_directory": str(cwd),
                "project_root": str(project_root),
                "python_executable": sys.executable,
                "auth_mode_env_var": os.environ.get("AUTH_MODE", "NOT_SET"),
                "ghl_client_id_env_var": (
                    os.environ.get("GHL_CLIENT_ID", "NOT_SET")[:10] + "..."
                    if os.environ.get("GHL_CLIENT_ID")
                    else "NOT_SET"
                ),
            },
            "files": {
                "env_file_exists": env_file.exists(),
                "tokens_json_exists": tokens_file.exists(),
                "standard_config_json_exists": standard_config_file.exists(),
            },
            "oauth_service": {
                "auth_mode": str(oauth_service.settings.auth_mode),
                "ghl_client_id": (
                    oauth_service.settings.ghl_client_id[:10] + "..."
                    if oauth_service.settings.ghl_client_id
                    else None
                ),
                "has_ghl_client_secret": bool(oauth_service.settings.ghl_client_secret),
                "supabase_url": oauth_service.settings.supabase_url,
                "has_supabase_access_key": bool(
                    oauth_service.settings.supabase_access_key
                ),
                "standard_auth_service_initialized": oauth_service._standard_auth
                is not None,
            },
            "token_status": {
                "custom_token_status": token_status,
                "custom_token_expires_at": token_expires_at,
            },
        }
