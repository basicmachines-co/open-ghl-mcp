"""Calendar tools for GoHighLevel MCP integration"""

from datetime import datetime, date
from typing import Dict, Any

from ...models.calendar import AppointmentCreate, AppointmentUpdate, AppointmentStatus
from ..params.calendars import (
    GetAppointmentsParams,
    GetAppointmentParams,
    CreateAppointmentParams,
    UpdateAppointmentParams,
    DeleteAppointmentParams,
    GetCalendarsParams,
    GetCalendarParams,
    GetFreeSlotsParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None


def _register_calendar_tools(_mcp, _get_client):
    """Register calendar tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    @mcp.tool()
    async def get_appointments(params: GetAppointmentsParams) -> Dict[str, Any]:
        """Get appointments for a contact"""
        client = await get_client(params.access_token)

        appointments = await client.get_appointments(
            contact_id=params.contact_id,
            location_id=params.location_id,
        )
        return {"success": True, "appointments": appointments.model_dump()}

    @mcp.tool()
    async def get_appointment(params: GetAppointmentParams) -> Dict[str, Any]:
        """Get a specific appointment"""
        client = await get_client(params.access_token)

        appointment = await client.get_appointment(
            params.appointment_id, params.location_id
        )
        return {"success": True, "appointment": appointment.model_dump()}

    @mcp.tool()
    async def create_appointment(params: CreateAppointmentParams) -> Dict[str, Any]:
        """Create a new appointment

        Important: Use timezone-aware ISO format for times to avoid 'slot no longer available' errors.
        Examples:
        - Central Time: '2025-06-09T11:00:00-05:00'
        - Eastern Time: '2025-06-09T11:00:00-04:00'
        - Pacific Time: '2025-06-09T11:00:00-07:00'

        The times should match the timezone of the calendar's location.
        """
        client = await get_client(params.access_token)

        # Parse ISO datetime strings
        start_time = datetime.fromisoformat(params.start_time.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(params.end_time.replace("Z", "+00:00"))

        appointment_data = AppointmentCreate(
            locationId=params.location_id,
            calendarId=params.calendar_id,
            contactId=params.contact_id,
            startTime=start_time,
            endTime=end_time,
            title=params.title,
            meetingLocationType=None,  # Default/optional
            appointmentStatus=(
                AppointmentStatus(params.appointment_status)
                if params.appointment_status
                else AppointmentStatus.CONFIRMED
            ),
            assignedUserId=params.assigned_user_id,
            notes=params.notes,
            address=params.address,
            ignoreDateRange=None,  # Default/optional
            toNotify=None,  # Default/optional
        )

        appointment = await client.create_appointment(appointment_data)
        return {"success": True, "appointment": appointment.model_dump()}

    @mcp.tool()
    async def update_appointment(params: UpdateAppointmentParams) -> Dict[str, Any]:
        """Update an existing appointment"""
        client = await get_client(params.access_token)

        # Parse ISO datetime strings if provided
        start_time = None
        end_time = None
        if params.start_time:
            start_time = datetime.fromisoformat(
                params.start_time.replace("Z", "+00:00")
            )
        if params.end_time:
            end_time = datetime.fromisoformat(params.end_time.replace("Z", "+00:00"))

        update_data = AppointmentUpdate(
            startTime=start_time,
            endTime=end_time,
            title=params.title,
            meetingLocationType=None,  # Default/optional
            appointmentStatus=(
                AppointmentStatus(params.appointment_status)
                if params.appointment_status
                else None
            ),
            assignedUserId=params.assigned_user_id,
            notes=params.notes,
            address=params.address,
            toNotify=None,  # Default/optional
        )

        appointment = await client.update_appointment(
            params.appointment_id, update_data, params.location_id
        )
        return {"success": True, "appointment": appointment.model_dump()}

    @mcp.tool()
    async def delete_appointment(params: DeleteAppointmentParams) -> Dict[str, Any]:
        """Delete an appointment"""
        client = await get_client(params.access_token)

        success = await client.delete_appointment(
            params.appointment_id, params.location_id
        )
        return {"success": success}

    @mcp.tool()
    async def get_calendars(params: GetCalendarsParams) -> Dict[str, Any]:
        """Get all calendars for a location"""
        client = await get_client(params.access_token)

        calendars = await client.get_calendars(params.location_id)
        return {"success": True, "calendars": calendars.model_dump()}

    @mcp.tool()
    async def get_calendar(params: GetCalendarParams) -> Dict[str, Any]:
        """Get a specific calendar"""
        client = await get_client(params.access_token)

        calendar = await client.get_calendar(params.calendar_id, params.location_id)
        return {"success": True, "calendar": calendar.model_dump()}

    @mcp.tool()
    async def get_free_slots(params: GetFreeSlotsParams) -> Dict[str, Any]:
        """Get available time slots for a calendar

        Important: Always provide both start_date and end_date for best results.
        Without end_date, the API may return limited or no available slots.

        Example:
        - start_date: '2025-06-09'
        - end_date: '2025-06-09'  # Same day or later

        The response will include slots in timezone-aware ISO format,
        which you should use directly when creating appointments.
        """
        client = await get_client(params.access_token)

        # Convert string dates to date objects
        start_date = date.fromisoformat(params.start_date)
        end_date = None
        if params.end_date:
            end_date = date.fromisoformat(params.end_date)

        slots = await client.get_free_slots(
            calendar_id=params.calendar_id,
            location_id=params.location_id,
            start_date=start_date,
            end_date=end_date,
            timezone=params.timezone,
        )
        return {"success": True, "slots": slots.model_dump()}
