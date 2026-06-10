"""Workflow parameter classes for MCP tools"""

from typing import Optional
from pydantic import BaseModel, Field


class GetWorkflowsParams(BaseModel):
    """Parameters for listing workflows in a location"""

    location_id: str = Field(..., description="The location ID to list workflows for")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class AddContactToWorkflowParams(BaseModel):
    """Parameters for adding a contact to a workflow"""

    contact_id: str = Field(..., description="The contact ID to enroll")
    workflow_id: str = Field(..., description="The workflow ID to enroll into")
    location_id: str = Field(
        ..., description="The location ID the contact/workflow belongs to"
    )
    event_start_time: Optional[str] = Field(
        None,
        description="Optional ISO 8601 time to start the workflow for this contact",
    )
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class RemoveContactFromWorkflowParams(BaseModel):
    """Parameters for removing a contact from a workflow"""

    contact_id: str = Field(..., description="The contact ID to remove")
    workflow_id: str = Field(..., description="The workflow ID to remove from")
    location_id: str = Field(
        ..., description="The location ID the contact/workflow belongs to"
    )
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )
