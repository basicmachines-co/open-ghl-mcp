"""Tests for the mcp.tools.calendars module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, date

from src.models.calendar import Calendar, Appointment, AppointmentList, CalendarList, FreeSlotsResult
from src.mcp.params.calendars import (
    GetCalendarsParams,
    GetCalendarParams,
    GetAppointmentsParams,
    GetAppointmentParams,
    CreateAppointmentParams,
    UpdateAppointmentParams,
    DeleteAppointmentParams,
    GetFreeSlotsParams,
)
from src.mcp.tools.calendars import _register_calendar_tools


class TestCalendarTools:
    """Test cases for calendar tools."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP instance."""
        mock = Mock()
        mock.tool = Mock(return_value=lambda func: func)
        return mock

    @pytest.fixture
    def mock_get_client(self):
        """Create a mock get_client function."""
        mock_client = AsyncMock()
        
        async def get_client(access_token=None):
            return mock_client
        
        return get_client, mock_client

    @pytest.fixture
    def setup_tools(self, mock_mcp, mock_get_client):
        """Set up calendar tools with mocks."""
        get_client_func, mock_client = mock_get_client
        
        # Capture the registered tools
        tools = {}
        
        def mock_tool_decorator():
            def decorator(func):
                # Store the function by its name
                tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool_decorator
        
        # Register the tools
        _register_calendar_tools(mock_mcp, get_client_func)
        
        return tools, mock_client

    @pytest.mark.asyncio
    async def test_get_calendars(self, setup_tools):
        """Test get_calendars tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_calendars = [
            Calendar(
                id="cal1",
                locationId="loc123",
                name="Calendar 1",
                description="First calendar",
                widgetType="default",
                widgetSlug="calendar-1",
                appointmentTitle="Meeting with {name}"
            ),
            Calendar(
                id="cal2",
                locationId="loc123",
                name="Calendar 2",
                description="Second calendar",
                widgetType="classic",
                widgetSlug="calendar-2",
                appointmentTitle="Call with {name}"
            )
        ]
        mock_result = CalendarList(calendars=mock_calendars, count=2)
        mock_client.get_calendars.return_value = mock_result
        
        # Create params
        params = GetCalendarsParams(
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_calendars"](params)
        
        # Verify
        assert result["success"] is True
        # The tool returns the CalendarList model dump, so we need to access the calendars list
        calendar_data = result["calendars"]
        assert len(calendar_data["calendars"]) == 2
        assert calendar_data["calendars"][0]["id"] == "cal1"
        assert calendar_data["calendars"][0]["name"] == "Calendar 1"
        assert calendar_data["calendars"][1]["id"] == "cal2"
        assert calendar_data["count"] == 2
        mock_client.get_calendars.assert_called_once_with("loc123")

    @pytest.mark.asyncio
    async def test_get_calendar(self, setup_tools):
        """Test get_calendar tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_calendar = Calendar(
            id="cal123",
            locationId="loc123",
            name="Test Calendar",
            description="Test calendar description",
            widgetType="default",
            widgetSlug="test-calendar",
            appointmentTitle="Appointment with {name}"
        )
        mock_client.get_calendar.return_value = mock_calendar
        
        # Create params
        params = GetCalendarParams(
            calendar_id="cal123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_calendar"](params)
        
        # Verify
        assert result["success"] is True
        assert result["calendar"]["id"] == "cal123"
        assert result["calendar"]["name"] == "Test Calendar"
        mock_client.get_calendar.assert_called_once_with("cal123", "loc123")

    @pytest.mark.asyncio
    async def test_get_appointments(self, setup_tools):
        """Test get_appointments tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_appointments = [
            Appointment(
                id="appt1",
                calendarId="cal123",
                locationId="loc123",
                contactId="contact1",
                startTime="2025-06-08T10:00:00Z",
                endTime="2025-06-08T11:00:00Z",
                title="Morning Meeting",
                appointmentStatus="confirmed",
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc)
            ),
            Appointment(
                id="appt2",
                calendarId="cal123",
                locationId="loc123",
                contactId="contact2",
                startTime="2025-06-08T14:00:00Z",
                endTime="2025-06-08T15:00:00Z",
                title="Afternoon Call",
                appointmentStatus="confirmed",
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc)
            )
        ]
        mock_result = AppointmentList(appointments=mock_appointments, count=2)
        mock_client.get_appointments.return_value = mock_result
        
        # Create params
        params = GetAppointmentsParams(
            contact_id="contact1",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_appointments"](params)
        
        # Verify
        assert result["success"] is True
        # The tool returns the AppointmentList model dump
        appointment_data = result["appointments"]
        assert len(appointment_data["appointments"]) == 2
        assert appointment_data["appointments"][0]["id"] == "appt1"
        assert appointment_data["appointments"][0]["title"] == "Morning Meeting"
        assert appointment_data["count"] == 2
        mock_client.get_appointments.assert_called_once_with(
            contact_id="contact1",
            location_id="loc123"
        )

    @pytest.mark.asyncio
    async def test_get_appointment(self, setup_tools):
        """Test get_appointment tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_appointment = Appointment(
            id="appt123",
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime="2025-06-08T10:00:00Z",
            endTime="2025-06-08T11:00:00Z",
            title="Test Appointment",
            appointmentStatus="confirmed",
            assignedUserId="user123",
            notes="Important meeting",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc)
        )
        mock_client.get_appointment.return_value = mock_appointment
        
        # Create params
        params = GetAppointmentParams(
            appointment_id="appt123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_appointment"](params)
        
        # Verify
        assert result["success"] is True
        assert result["appointment"]["id"] == "appt123"
        assert result["appointment"]["title"] == "Test Appointment"
        assert result["appointment"]["appointmentStatus"] == "confirmed"
        mock_client.get_appointment.assert_called_once_with("appt123", "loc123")

    @pytest.mark.asyncio
    async def test_create_appointment(self, setup_tools):
        """Test create_appointment tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_appointment = Appointment(
            id="appt123",
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime="2025-06-08T10:00:00Z",
            endTime="2025-06-08T11:00:00Z",
            title="New Appointment",
            appointmentStatus="confirmed",
            assignedUserId="user123",
            notes="Created appointment",
            address="123 Main St",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc)
        )
        mock_client.create_appointment.return_value = mock_appointment
        
        # Create params
        params = CreateAppointmentParams(
            calendar_id="cal123",
            location_id="loc123",
            contact_id="contact123",
            start_time="2025-06-08T10:00:00Z",
            end_time="2025-06-08T11:00:00Z",
            title="New Appointment",
            assigned_user_id="user123",
            address="123 Main St",
            notes="Created appointment",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["create_appointment"](params)
        
        # Verify
        assert result["success"] is True
        assert result["appointment"]["id"] == "appt123"
        assert result["appointment"]["title"] == "New Appointment"
        assert result["appointment"]["address"] == "123 Main St"
        
        # Verify the client was called with correct data
        create_call_args = mock_client.create_appointment.call_args[0][0]
        assert create_call_args.calendarId == "cal123"
        assert create_call_args.contactId == "contact123"
        # The tool converts the datetime string to a datetime object
        assert create_call_args.startTime == datetime(2025, 6, 8, 10, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_update_appointment(self, setup_tools):
        """Test update_appointment tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_appointment = Appointment(
            id="appt123",
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime="2025-06-08T14:00:00Z",
            endTime="2025-06-08T15:00:00Z",
            title="Updated Appointment",
            appointmentStatus="confirmed",
            notes="Updated notes",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc)
        )
        mock_client.update_appointment.return_value = mock_appointment
        
        # Create params
        params = UpdateAppointmentParams(
            appointment_id="appt123",
            location_id="loc123",
            start_time="2025-06-08T14:00:00Z",
            end_time="2025-06-08T15:00:00Z",
            title="Updated Appointment",
            appointment_status="confirmed",
            notes="Updated notes",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["update_appointment"](params)
        
        # Verify
        assert result["success"] is True
        assert result["appointment"]["title"] == "Updated Appointment"
        # model_dump returns datetime objects
        assert result["appointment"]["startTime"] == datetime(2025, 6, 8, 14, 0, tzinfo=timezone.utc)
        
        # Verify client call
        update_data = mock_client.update_appointment.call_args[0][1]
        assert update_data.startTime == datetime(2025, 6, 8, 14, 0, tzinfo=timezone.utc)
        assert update_data.title == "Updated Appointment"

    @pytest.mark.asyncio
    async def test_delete_appointment_success(self, setup_tools):
        """Test delete_appointment tool with success."""
        tools, mock_client = setup_tools
        
        # Mock successful deletion
        mock_client.delete_appointment.return_value = True
        
        # Create params
        params = DeleteAppointmentParams(
            appointment_id="appt123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["delete_appointment"](params)
        
        # Verify
        assert result["success"] is True
        mock_client.delete_appointment.assert_called_once_with("appt123", "loc123")

    @pytest.mark.asyncio
    async def test_delete_appointment_failure(self, setup_tools):
        """Test delete_appointment tool with failure."""
        tools, mock_client = setup_tools
        
        # Mock failed deletion
        mock_client.delete_appointment.return_value = False
        
        # Create params
        params = DeleteAppointmentParams(
            appointment_id="appt123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["delete_appointment"](params)
        
        # Verify
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_get_free_slots(self, setup_tools):
        """Test get_free_slots tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        from src.models.calendar import FreeSlot
        mock_slots = FreeSlotsResult(
            date="2025-06-08",
            slots=[
                FreeSlot(
                    startTime="2025-06-08T09:00:00Z",
                    endTime="2025-06-08T10:00:00Z",
                    available=True
                ),
                FreeSlot(
                    startTime="2025-06-08T11:00:00Z",
                    endTime="2025-06-08T12:00:00Z",
                    available=True
                ),
                FreeSlot(
                    startTime="2025-06-08T14:00:00Z",
                    endTime="2025-06-08T15:00:00Z",
                    available=True
                )
            ]
        )
        mock_client.get_free_slots.return_value = mock_slots
        
        # Create params
        params = GetFreeSlotsParams(
            calendar_id="cal123",
            location_id="loc123",
            start_date="2025-06-08",
            end_date="2025-06-08",
            timezone="America/Chicago",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_free_slots"](params)
        
        # Verify
        assert result["success"] is True
        # The tool returns the FreeSlotsResult model dump
        slots_data = result["slots"]
        assert len(slots_data["slots"]) == 3
        assert slots_data["date"] == "2025-06-08"
        # model_dump converts datetime to datetime objects
        assert slots_data["slots"][0]["startTime"] == datetime(2025, 6, 8, 9, 0, tzinfo=timezone.utc)
        assert slots_data["slots"][1]["startTime"] == datetime(2025, 6, 8, 11, 0, tzinfo=timezone.utc)
        mock_client.get_free_slots.assert_called_once_with(
            calendar_id="cal123",
            location_id="loc123",
            start_date=date(2025, 6, 8),
            end_date=date(2025, 6, 8),
            timezone="America/Chicago"
        )