"""Contact note and task tools for GoHighLevel MCP integration"""

from typing import Dict, Any

from ...models.notes_tasks import NoteCreate, NoteUpdate, TaskCreate, TaskUpdate
from ..params.notes_tasks import (
    GetNotesParams,
    GetNoteParams,
    CreateNoteParams,
    UpdateNoteParams,
    DeleteNoteParams,
    GetTasksParams,
    GetTaskParams,
    CreateTaskParams,
    UpdateTaskParams,
    CompleteTaskParams,
    DeleteTaskParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None


def _register_notes_tasks_tools(_mcp, _get_client):
    """Register contact note and task tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    # --- Notes ---

    @mcp.tool()
    async def get_contact_notes(params: GetNotesParams) -> Dict[str, Any]:
        """List all notes for a contact"""
        client = await get_client(params.access_token)

        result = await client.get_notes(params.contact_id, params.location_id)
        return {
            "success": True,
            "notes": [n.model_dump() for n in result.notes],
            "count": result.count,
        }

    @mcp.tool()
    async def get_contact_note(params: GetNoteParams) -> Dict[str, Any]:
        """Get a single note for a contact"""
        client = await get_client(params.access_token)

        note = await client.get_note(
            params.contact_id, params.note_id, params.location_id
        )
        return {"success": True, "note": note.model_dump()}

    @mcp.tool()
    async def create_contact_note(params: CreateNoteParams) -> Dict[str, Any]:
        """Create a note on a contact"""
        client = await get_client(params.access_token)

        note_data = NoteCreate(
            body=params.body,
            title=params.title,
            userId=params.user_id,
            color=params.color,
            pinned=params.pinned,
        )
        note = await client.create_note(
            params.contact_id, note_data, params.location_id
        )
        return {"success": True, "note": note.model_dump()}

    @mcp.tool()
    async def update_contact_note(params: UpdateNoteParams) -> Dict[str, Any]:
        """Update a note on a contact"""
        client = await get_client(params.access_token)

        update_data = NoteUpdate(
            body=params.body,
            title=params.title,
            userId=params.user_id,
            color=params.color,
            pinned=params.pinned,
        )
        note = await client.update_note(
            params.contact_id, params.note_id, update_data, params.location_id
        )
        return {"success": True, "note": note.model_dump()}

    @mcp.tool()
    async def delete_contact_note(params: DeleteNoteParams) -> Dict[str, Any]:
        """Delete a note from a contact"""
        client = await get_client(params.access_token)

        success = await client.delete_note(
            params.contact_id, params.note_id, params.location_id
        )
        return {
            "success": success,
            "message": (
                "Note deleted successfully" if success else "Failed to delete note"
            ),
        }

    # --- Tasks ---

    @mcp.tool()
    async def get_contact_tasks(params: GetTasksParams) -> Dict[str, Any]:
        """List all tasks for a contact"""
        client = await get_client(params.access_token)

        result = await client.get_tasks(params.contact_id, params.location_id)
        return {
            "success": True,
            "tasks": [t.model_dump() for t in result.tasks],
            "count": result.count,
        }

    @mcp.tool()
    async def get_contact_task(params: GetTaskParams) -> Dict[str, Any]:
        """Get a single task for a contact"""
        client = await get_client(params.access_token)

        task = await client.get_task(
            params.contact_id, params.task_id, params.location_id
        )
        return {"success": True, "task": task.model_dump()}

    @mcp.tool()
    async def create_contact_task(params: CreateTaskParams) -> Dict[str, Any]:
        """Create a task on a contact"""
        client = await get_client(params.access_token)

        task_data = TaskCreate(
            title=params.title,
            dueDate=params.due_date,
            completed=params.completed,
            body=params.body,
            assignedTo=params.assigned_to,
        )
        task = await client.create_task(
            params.contact_id, task_data, params.location_id
        )
        return {"success": True, "task": task.model_dump()}

    @mcp.tool()
    async def update_contact_task(params: UpdateTaskParams) -> Dict[str, Any]:
        """Update a task on a contact"""
        client = await get_client(params.access_token)

        update_data = TaskUpdate(
            title=params.title,
            body=params.body,
            dueDate=params.due_date,
            completed=params.completed,
            assignedTo=params.assigned_to,
        )
        task = await client.update_task(
            params.contact_id, params.task_id, update_data, params.location_id
        )
        return {"success": True, "task": task.model_dump()}

    @mcp.tool()
    async def complete_contact_task(params: CompleteTaskParams) -> Dict[str, Any]:
        """Set the completed status of a contact's task"""
        client = await get_client(params.access_token)

        task = await client.update_task_completed(
            params.contact_id, params.task_id, params.completed, params.location_id
        )
        return {"success": True, "task": task.model_dump()}

    @mcp.tool()
    async def delete_contact_task(params: DeleteTaskParams) -> Dict[str, Any]:
        """Delete a task from a contact"""
        client = await get_client(params.access_token)

        success = await client.delete_task(
            params.contact_id, params.task_id, params.location_id
        )
        return {
            "success": success,
            "message": (
                "Task deleted successfully" if success else "Failed to delete task"
            ),
        }
