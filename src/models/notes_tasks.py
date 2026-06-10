"""Models for GoHighLevel contact notes and tasks"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class Note(BaseModel):
    """GoHighLevel contact note"""

    id: Optional[str] = None
    body: Optional[str] = None
    userId: Optional[str] = None
    dateAdded: Optional[datetime] = None
    contactId: Optional[str] = None
    title: Optional[str] = None
    color: Optional[str] = None
    pinned: Optional[bool] = None

    model_config = {"populate_by_name": True}


class NoteCreate(BaseModel):
    """Model for creating a contact note"""

    body: str
    userId: Optional[str] = None
    title: Optional[str] = None
    color: Optional[str] = None
    pinned: Optional[bool] = None


class NoteUpdate(BaseModel):
    """Model for updating a contact note"""

    body: Optional[str] = None
    userId: Optional[str] = None
    title: Optional[str] = None
    color: Optional[str] = None
    pinned: Optional[bool] = None


class NoteList(BaseModel):
    """Response model for a list of notes"""

    notes: List[Note]
    count: int


class Task(BaseModel):
    """GoHighLevel contact task"""

    id: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    assignedTo: Optional[str] = None
    dueDate: Optional[datetime] = None
    completed: Optional[bool] = None
    contactId: Optional[str] = None

    model_config = {"populate_by_name": True}


class TaskCreate(BaseModel):
    """Model for creating a contact task"""

    title: str
    dueDate: str  # ISO 8601 datetime string
    completed: bool = False
    body: Optional[str] = None
    assignedTo: Optional[str] = None


class TaskUpdate(BaseModel):
    """Model for updating a contact task"""

    title: Optional[str] = None
    body: Optional[str] = None
    dueDate: Optional[str] = None
    completed: Optional[bool] = None
    assignedTo: Optional[str] = None


class TaskList(BaseModel):
    """Response model for a list of tasks"""

    tasks: List[Task]
    count: int
