"""Contact notes and tasks client for GoHighLevel API v2"""

from .base import BaseGoHighLevelClient
from ..models.notes_tasks import (
    Note,
    NoteCreate,
    NoteUpdate,
    NoteList,
    Task,
    TaskCreate,
    TaskUpdate,
    TaskList,
)


class NotesTasksClient(BaseGoHighLevelClient):
    """Client for contact notes and tasks endpoints (location-token scoped)"""

    # --- Notes ---

    async def get_notes(self, contact_id: str, location_id: str) -> NoteList:
        """Get all notes for a contact"""
        response = await self._request(
            "GET",
            f"/contacts/{contact_id}/notes",
            location_id=location_id,
        )
        data = response.json()
        notes = [Note(**n) for n in data.get("notes", [])]
        return NoteList(notes=notes, count=len(notes))

    async def get_note(self, contact_id: str, note_id: str, location_id: str) -> Note:
        """Get a specific note for a contact"""
        response = await self._request(
            "GET",
            f"/contacts/{contact_id}/notes/{note_id}",
            location_id=location_id,
        )
        data = response.json()
        return Note(**data.get("note", data))

    async def create_note(
        self, contact_id: str, note: NoteCreate, location_id: str
    ) -> Note:
        """Create a note on a contact"""
        response = await self._request(
            "POST",
            f"/contacts/{contact_id}/notes",
            json=note.model_dump(exclude_none=True),
            location_id=location_id,
        )
        data = response.json()
        return Note(**data.get("note", data))

    async def update_note(
        self, contact_id: str, note_id: str, updates: NoteUpdate, location_id: str
    ) -> Note:
        """Update a note on a contact"""
        response = await self._request(
            "PUT",
            f"/contacts/{contact_id}/notes/{note_id}",
            json=updates.model_dump(exclude_none=True),
            location_id=location_id,
        )
        data = response.json()
        return Note(**data.get("note", data))

    async def delete_note(
        self, contact_id: str, note_id: str, location_id: str
    ) -> bool:
        """Delete a note from a contact"""
        response = await self._request(
            "DELETE",
            f"/contacts/{contact_id}/notes/{note_id}",
            location_id=location_id,
        )
        data = response.json() if response.content else {}
        return bool(data.get("succeded", response.status_code in (200, 201)))

    # --- Tasks ---

    async def get_tasks(self, contact_id: str, location_id: str) -> TaskList:
        """Get all tasks for a contact"""
        response = await self._request(
            "GET",
            f"/contacts/{contact_id}/tasks",
            location_id=location_id,
        )
        data = response.json()
        tasks = [Task(**t) for t in data.get("tasks", [])]
        return TaskList(tasks=tasks, count=len(tasks))

    async def get_task(self, contact_id: str, task_id: str, location_id: str) -> Task:
        """Get a specific task for a contact"""
        response = await self._request(
            "GET",
            f"/contacts/{contact_id}/tasks/{task_id}",
            location_id=location_id,
        )
        data = response.json()
        return Task(**data.get("task", data))

    async def create_task(
        self, contact_id: str, task: TaskCreate, location_id: str
    ) -> Task:
        """Create a task on a contact"""
        response = await self._request(
            "POST",
            f"/contacts/{contact_id}/tasks",
            json=task.model_dump(exclude_none=True),
            location_id=location_id,
        )
        data = response.json()
        return Task(**data.get("task", data))

    async def update_task(
        self, contact_id: str, task_id: str, updates: TaskUpdate, location_id: str
    ) -> Task:
        """Update a task on a contact"""
        response = await self._request(
            "PUT",
            f"/contacts/{contact_id}/tasks/{task_id}",
            json=updates.model_dump(exclude_none=True),
            location_id=location_id,
        )
        data = response.json()
        return Task(**data.get("task", data))

    async def update_task_completed(
        self, contact_id: str, task_id: str, completed: bool, location_id: str
    ) -> Task:
        """Update only the completed status of a task"""
        response = await self._request(
            "PUT",
            f"/contacts/{contact_id}/tasks/{task_id}/completed",
            json={"completed": completed},
            location_id=location_id,
        )
        data = response.json()
        return Task(**data.get("task", data))

    async def delete_task(
        self, contact_id: str, task_id: str, location_id: str
    ) -> bool:
        """Delete a task from a contact"""
        response = await self._request(
            "DELETE",
            f"/contacts/{contact_id}/tasks/{task_id}",
            location_id=location_id,
        )
        data = response.json() if response.content else {}
        return bool(data.get("succeded", response.status_code in (200, 201)))
