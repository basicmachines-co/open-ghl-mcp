"""Unit tests for the contact notes and tasks client"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.notes_tasks import NotesTasksClient
from src.models.notes_tasks import NoteCreate, NoteUpdate, TaskCreate, TaskUpdate

CONTACT_ID = "contact_abc"
LOCATION_ID = "loc_123"


@pytest.fixture
def client():
    service = MagicMock()
    service.get_valid_token = AsyncMock(return_value="agency_token")
    service.get_location_token = AsyncMock(return_value="location_token")
    return NotesTasksClient(service)


def _response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b"{}"
    resp.json.return_value = payload
    return resp


class TestNotes:
    @pytest.mark.asyncio
    async def test_get_notes_uses_location_token(self, client):
        payload = {"notes": [{"id": "n1", "body": "Called the lead"}]}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            result = await client.get_notes(CONTACT_ID, LOCATION_ID)

        args, kwargs = req.call_args
        assert args[0] == "GET"
        assert args[1] == f"/contacts/{CONTACT_ID}/notes"
        # contact sub-resources require a location token
        assert kwargs["location_id"] == LOCATION_ID
        assert result.count == 1
        assert result.notes[0].body == "Called the lead"

    @pytest.mark.asyncio
    async def test_create_note_sends_body(self, client):
        payload = {"note": {"id": "n2", "body": "Follow up"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload, status=201)
            note = await client.create_note(
                CONTACT_ID, NoteCreate(body="Follow up", pinned=True), LOCATION_ID
            )

        args, kwargs = req.call_args
        assert args[0] == "POST"
        assert kwargs["json"] == {"body": "Follow up", "pinned": True}
        assert note.id == "n2"

    @pytest.mark.asyncio
    async def test_update_note(self, client):
        payload = {"note": {"id": "n1", "body": "Edited"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            note = await client.update_note(
                CONTACT_ID, "n1", NoteUpdate(body="Edited"), LOCATION_ID
            )

        args, kwargs = req.call_args
        assert args[0] == "PUT"
        assert args[1] == f"/contacts/{CONTACT_ID}/notes/n1"
        assert note.body == "Edited"

    @pytest.mark.asyncio
    async def test_delete_note(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response({"succeded": True})
            ok = await client.delete_note(CONTACT_ID, "n1", LOCATION_ID)
        assert ok is True


class TestTasks:
    @pytest.mark.asyncio
    async def test_get_tasks_parses_list(self, client):
        payload = {"tasks": [{"id": "t1", "title": "Call back", "completed": False}]}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            result = await client.get_tasks(CONTACT_ID, LOCATION_ID)

        assert result.count == 1
        assert result.tasks[0].title == "Call back"

    @pytest.mark.asyncio
    async def test_create_task_sends_required_fields(self, client):
        payload = {"task": {"id": "t2", "title": "Demo"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload, status=201)
            task = await client.create_task(
                CONTACT_ID,
                TaskCreate(title="Demo", dueDate="2026-06-10T17:00:00Z"),
                LOCATION_ID,
            )

        args, kwargs = req.call_args
        assert args[0] == "POST"
        assert kwargs["json"] == {
            "title": "Demo",
            "dueDate": "2026-06-10T17:00:00Z",
            "completed": False,
        }
        assert task.id == "t2"

    @pytest.mark.asyncio
    async def test_update_task(self, client):
        payload = {"task": {"id": "t1", "title": "Updated"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            task = await client.update_task(
                CONTACT_ID, "t1", TaskUpdate(title="Updated"), LOCATION_ID
            )
        assert task.title == "Updated"

    @pytest.mark.asyncio
    async def test_complete_task_hits_completed_endpoint(self, client):
        payload = {"task": {"id": "t1", "completed": True}}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            task = await client.update_task_completed(
                CONTACT_ID, "t1", True, LOCATION_ID
            )

        args, kwargs = req.call_args
        assert args[0] == "PUT"
        assert args[1] == f"/contacts/{CONTACT_ID}/tasks/t1/completed"
        assert kwargs["json"] == {"completed": True}
        assert task.completed is True

    @pytest.mark.asyncio
    async def test_delete_task(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response({"succeded": True})
            ok = await client.delete_task(CONTACT_ID, "t1", LOCATION_ID)
        assert ok is True
