"""Models for GoHighLevel workflows"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class Workflow(BaseModel):
    """GoHighLevel workflow"""

    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    version: Optional[int] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    locationId: Optional[str] = None

    model_config = {"populate_by_name": True}


class WorkflowList(BaseModel):
    """Response model for a list of workflows"""

    workflows: List[Workflow]
    count: int
