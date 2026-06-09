"""Form tools for GoHighLevel MCP integration"""

from typing import Dict, Any

from ...models.form import FormFileUploadRequest
from ..params.forms import (
    GetFormsParams,
    GetAllSubmissionsParams,
    UploadFormFileParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None


def _register_form_tools(_mcp, _get_client):
    """Register form tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    @mcp.tool()
    async def get_forms(params: GetFormsParams) -> Dict[str, Any]:
        """Get all forms for a location"""
        client = await get_client(params.access_token)

        form_list = await client.get_forms(
            location_id=params.location_id, limit=params.limit, skip=params.skip
        )

        return {
            "success": True,
            "forms": [form.model_dump() for form in form_list.forms],
            "total": form_list.total,
            "count": form_list.count,
        }

    # NOTE: The following endpoints are not supported by the GoHighLevel API:
    # - GET /forms/{id} - Returns 401 "This route is not yet supported by the IAM Service"
    # - GET /forms/{id}/submissions - Returns 404 Not Found
    # These tools have been removed from the implementation

    @mcp.tool()
    async def get_all_form_submissions(
        params: GetAllSubmissionsParams,
    ) -> Dict[str, Any]:
        """Get all form submissions for a location, optionally filtered by form or contact"""
        client = await get_client(params.access_token)

        submissions = await client.get_all_submissions(
            location_id=params.location_id,
            form_id=params.form_id,
            contact_id=params.contact_id,
            start_date=params.start_date,
            end_date=params.end_date,
            limit=params.limit,
            skip=params.skip,
        )

        return {
            "success": True,
            "submissions": [sub.model_dump() for sub in submissions.submissions],
            "total": submissions.total,
            "count": submissions.count,
        }

    # NOTE: POST /forms/submit endpoint has been removed
    # The unauthenticated endpoint returns 401 and requires further investigation

    @mcp.tool()
    async def upload_form_file(params: UploadFormFileParams) -> Dict[str, Any]:
        """Upload a file to a form's custom field

        The file_content should be base64 encoded.
        """
        client = await get_client(params.access_token)

        file_upload = FormFileUploadRequest(
            contactId=params.contact_id,
            locationId=params.location_id,
            fieldId=params.field_id,
            fileName=params.file_name,
            fileContent=params.file_content,
            contentType=params.content_type,
        )

        result = await client.upload_form_file(file_upload)

        return {"success": True, "result": result}
