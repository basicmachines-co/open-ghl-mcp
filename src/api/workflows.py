"""Workflows client for GoHighLevel API v2"""

from typing import Optional, Dict, Any

from .base import BaseGoHighLevelClient
from ..models.workflow import Workflow, WorkflowList


class WorkflowsClient(BaseGoHighLevelClient):
    """Client for workflow endpoints and contact/workflow enrollment"""

    async def get_workflows(self, location_id: str) -> WorkflowList:
        """Get all workflows for a location"""
        response = await self._request(
            "GET",
            "/workflows/",
            params={"locationId": location_id},
            location_id=location_id,
        )
        data = response.json()
        workflows = [Workflow(**w) for w in data.get("workflows", [])]
        return WorkflowList(workflows=workflows, count=len(workflows))

    async def add_contact_to_workflow(
        self,
        contact_id: str,
        workflow_id: str,
        location_id: str,
        event_start_time: Optional[str] = None,
    ) -> bool:
        """Add a contact to a workflow

        Args:
            event_start_time: Optional ISO 8601 time to start the workflow
        """
        json_body: Dict[str, Any] = {}
        if event_start_time:
            json_body["eventStartTime"] = event_start_time
        response = await self._request(
            "POST",
            f"/contacts/{contact_id}/workflow/{workflow_id}",
            json=json_body or None,
            location_id=location_id,
        )
        data = response.json() if response.content else {}
        return bool(data.get("succeded", response.status_code in (200, 201)))

    async def remove_contact_from_workflow(
        self, contact_id: str, workflow_id: str, location_id: str
    ) -> bool:
        """Remove a contact from a workflow"""
        response = await self._request(
            "DELETE",
            f"/contacts/{contact_id}/workflow/{workflow_id}",
            location_id=location_id,
        )
        data = response.json() if response.content else {}
        return bool(data.get("succeded", response.status_code in (200, 201)))
