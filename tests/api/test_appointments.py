"""Test appointment creation fix for minimal API response"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.calendars import CalendarsClient
from src.models.calendar import AppointmentCreate, Appointment


class TestAppointmentCreationFix:
    """Test the appointment creation response handling fix"""

    @pytest.fixture
    def mock_oauth_service(self):
        """Create a mock OAuth service"""
        mock = AsyncMock()
        mock.get_location_token = AsyncMock(return_value="test_location_token")
        return mock

    @pytest.fixture
    def calendars_client(self, mock_oauth_service):
        """Create a calendars client with mocked OAuth"""
        return CalendarsClient(mock_oauth_service)

    @pytest.mark.asyncio
    async def test_create_appointment_minimal_response(self, calendars_client):
        """Test that create_appointment handles minimal API response correctly"""
        # Test data
        location_id = "test_location_id"
        calendar_id = "test_calendar_id"
        contact_id = "test_contact_id"
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(minutes=30)

        appointment_data = AppointmentCreate(
            calendarId=calendar_id,
            locationId=location_id,
            contactId=contact_id,
            startTime=start_time,
            endTime=end_time,
            title="Test Appointment",
            appointmentStatus="confirmed",
            notes="Test notes",
        )

        # Mock the minimal response from GoHighLevel API
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "new_appointment_id",
            "calendarId": calendar_id,
            "contactId": contact_id,
            "title": "Test Appointment",
            "status": "booked",
            "appoinmentStatus": "confirmed",  # Note the typo in API
            "assignedUserId": "test_user_id",
            "address": "https://zoom.us/j/123456",
            "isRecurring": False,
            "traceId": "test-trace-id",
        }

        # Patch the _request method
        with patch.object(
            calendars_client, "_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            # Call create_appointment
            result = await calendars_client.create_appointment(appointment_data)

            # Verify the result is properly constructed
            assert isinstance(result, Appointment)
            assert result.id == "new_appointment_id"
            assert result.calendarId == calendar_id
            assert result.contactId == contact_id
            assert result.locationId == location_id  # Should be preserved from request
            assert result.title == "Test Appointment"
            assert result.appointmentStatus == "confirmed"  # Should handle the typo
            assert result.startTime == start_time  # Should be preserved from request
            assert result.endTime == end_time  # Should be preserved from request
            assert result.notes == "Test notes"  # Should be preserved from request
            assert result.address == "https://zoom.us/j/123456"  # From response

    @pytest.mark.asyncio
    async def test_create_appointment_error_response(self, calendars_client):
        """Test that create_appointment handles error responses (400) correctly"""
        # Test data
        appointment_data = AppointmentCreate(
            calendarId="test_calendar_id",
            locationId="test_location_id",
            contactId="test_contact_id",
            startTime=datetime.now() + timedelta(days=1),
            endTime=datetime.now() + timedelta(days=1, minutes=30),
            title="Test Appointment",
            appointmentStatus="confirmed",
        )

        # Mock the error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "The slot you have selected is no longer available.",
            "error": "Bad Request",
            "statusCode": 400,
            "traceId": "error-trace-id",
        }

        # Patch the _request method to raise an exception
        from src.utils.exceptions import ValidationError

        with patch.object(
            calendars_client, "_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = ValidationError(
                "The slot you have selected is no longer available.",
                status_code=400,
                response_data=mock_response.json(),
            )

            # Call should raise the validation error
            with pytest.raises(ValidationError) as exc_info:
                await calendars_client.create_appointment(appointment_data)

            assert "slot you have selected is no longer available" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_create_appointment_with_datetime_serialization(
        self, calendars_client
    ):
        """Test that datetime objects are properly serialized to ISO strings"""
        appointment_data = AppointmentCreate(
            calendarId="test_calendar_id",
            locationId="test_location_id",
            contactId="test_contact_id",
            startTime=datetime(2025, 6, 10, 14, 0, 0),
            endTime=datetime(2025, 6, 10, 14, 30, 0),
            title="Test Appointment",
        )

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "new_id",
            "calendarId": "test_calendar_id",
            "contactId": "test_contact_id",
            "title": "Test Appointment",
            "status": "booked",
        }

        with patch.object(
            calendars_client, "_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await calendars_client.create_appointment(appointment_data)

            # Check that the request was made with ISO format times
            call_args = mock_request.call_args
            request_data = call_args[1]["json"]
            assert request_data["startTime"] == "2025-06-10T14:00:00"
            assert request_data["endTime"] == "2025-06-10T14:30:00"
