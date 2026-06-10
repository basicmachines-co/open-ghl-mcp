"""Note and task parameter classes for MCP tools"""

from typing import Optional
from pydantic import BaseModel, Field


class _ContactScoped(BaseModel):
    """Common fields for contact-scoped note/task operations"""

    contact_id: str = Field(..., description="The contact ID")
    location_id: str = Field(
        ..., description="The location ID the contact belongs to (for auth token)"
    )
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


# --- Notes ---


class GetNotesParams(_ContactScoped):
    """Parameters for listing a contact's notes"""


class GetNoteParams(_ContactScoped):
    """Parameters for getting a single note"""

    note_id: str = Field(..., description="The note ID to retrieve")


class CreateNoteParams(_ContactScoped):
    """Parameters for creating a note"""

    body: str = Field(..., description="The note text/body")
    title: Optional[str] = Field(None, description="Optional note title")
    user_id: Optional[str] = Field(None, description="User ID to attribute the note to")
    color: Optional[str] = Field(None, description="Optional display color")
    pinned: Optional[bool] = Field(None, description="Whether to pin the note")


class UpdateNoteParams(_ContactScoped):
    """Parameters for updating a note"""

    note_id: str = Field(..., description="The note ID to update")
    body: Optional[str] = Field(None, description="The note text/body")
    title: Optional[str] = Field(None, description="Optional note title")
    user_id: Optional[str] = Field(None, description="User ID to attribute the note to")
    color: Optional[str] = Field(None, description="Optional display color")
    pinned: Optional[bool] = Field(None, description="Whether to pin the note")


class DeleteNoteParams(_ContactScoped):
    """Parameters for deleting a note"""

    note_id: str = Field(..., description="The note ID to delete")


# --- Tasks ---


class GetTasksParams(_ContactScoped):
    """Parameters for listing a contact's tasks"""


class GetTaskParams(_ContactScoped):
    """Parameters for getting a single task"""

    task_id: str = Field(..., description="The task ID to retrieve")


class CreateTaskParams(_ContactScoped):
    """Parameters for creating a task"""

    title: str = Field(..., description="The task title")
    due_date: str = Field(
        ..., description="Due date as ISO 8601 datetime (e.g. 2026-06-10T17:00:00Z)"
    )
    completed: bool = Field(False, description="Whether the task is already completed")
    body: Optional[str] = Field(None, description="Optional task description/body")
    assigned_to: Optional[str] = Field(
        None, description="User ID the task is assigned to"
    )


class UpdateTaskParams(_ContactScoped):
    """Parameters for updating a task"""

    task_id: str = Field(..., description="The task ID to update")
    title: Optional[str] = Field(None, description="The task title")
    due_date: Optional[str] = Field(None, description="Due date as ISO 8601 datetime")
    completed: Optional[bool] = Field(None, description="Whether the task is completed")
    body: Optional[str] = Field(None, description="Optional task description/body")
    assigned_to: Optional[str] = Field(
        None, description="User ID the task is assigned to"
    )


class CompleteTaskParams(_ContactScoped):
    """Parameters for toggling a task's completed status"""

    task_id: str = Field(..., description="The task ID to update")
    completed: bool = Field(..., description="The completed status to set")


class DeleteTaskParams(_ContactScoped):
    """Parameters for deleting a task"""

    task_id: str = Field(..., description="The task ID to delete")
