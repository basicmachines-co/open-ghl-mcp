"""Test calendar endpoint fixes"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.calendars import CalendarsClient
from src.models.calendar import FreeSlotsResult, FreeSlot


class TestCalendarsFix:
    """Test the calendar endpoint fixes"""

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
    async def test_get_free_slots_numeric_timestamps(self, calendars_client):
        """Test that get_free_slots uses numeric timestamps and no locationId in params"""
        calendar_id = "test_calendar_id"
        location_id = "test_location_id"
        start_date = date(2025, 6, 10)
        end_date = date(2025, 6, 11)
        timezone = "America/Chicago"

        # Mock the response from the API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "2025-06-10": {
                "slots": [
                    "2025-06-10T11:00:00-05:00",
                    "2025-06-10T11:30:00-05:00",
                    "2025-06-10T13:00:00-05:00",
                ]
            },
            "traceId": "test-trace-id",
        }

        # Patch the _request method to capture the request params
        with patch.object(
            calendars_client, "_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            # Call get_free_slots
            result = await calendars_client.get_free_slots(
                calendar_id=calendar_id,
                location_id=location_id,
                start_date=start_date,
                end_date=end_date,
                timezone=timezone,
            )

            # Verify the request was made correctly
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check that locationId is NOT in the params
            assert "locationId" not in call_args[1]["params"]

            # Check that timestamps are numeric (milliseconds)
            assert isinstance(call_args[1]["params"]["startDate"], int)
            assert isinstance(call_args[1]["params"]["endDate"], int)

            # Verify the timestamps are correct
            start_timestamp = int(
                datetime.combine(start_date, datetime.min.time()).timestamp() * 1000
            )
            end_timestamp = int(
                datetime.combine(end_date, datetime.min.time()).timestamp() * 1000
            )
            assert call_args[1]["params"]["startDate"] == start_timestamp
            assert call_args[1]["params"]["endDate"] == end_timestamp

            # Check timezone is included
            assert call_args[1]["params"]["timezone"] == timezone

            # Verify the result is parsed correctly
            assert isinstance(result, FreeSlotsResult)
            assert len(result.slots) == 3
            assert all(isinstance(slot, FreeSlot) for slot in result.slots)

            # Check the first slot details
            first_slot = result.slots[0]
            # The model converts strings to datetime objects
            assert isinstance(first_slot.startTime, datetime)
            assert first_slot.available is True

    @pytest.mark.asyncio
    async def test_create_appointment_endpoint_path(self, calendars_client):
        """Test that create_appointment uses the correct endpoint path"""
        from src.models.calendar import AppointmentCreate, Appointment

        # Create appointment data
        appointment_data = AppointmentCreate(
            locationId="test_location_id",
            calendarId="test_calendar_id",
            contactId="test_contact_id",
            startTime=datetime(2025, 6, 10, 11, 0, 0),
            endTime=datetime(2025, 6, 10, 11, 30, 0),
            title="Test Appointment",
            appointmentStatus="confirmed",
        )

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "new_appointment_id",
            "calendarId": "test_calendar_id",
            "contactId": "test_contact_id",
            "title": "Test Appointment",
            "status": "booked",
            "appoinmentStatus": "confirmed",
            "assignedUserId": "test_user_id",
            "address": "https://zoom.us/j/123456",
            "isRecurring": False,
        }

        # Mock a complete appointment response
        complete_response = {
            "id": "new_appointment_id",
            "locationId": "test_location_id",
            "calendarId": "test_calendar_id",
            "contactId": "test_contact_id",
            "title": "Test Appointment",
            "startTime": "2025-06-10T11:00:00-05:00",
            "endTime": "2025-06-10T11:30:00-05:00",
            "appointmentStatus": "confirmed",
            "assignedUserId": "test_user_id",
            "address": "https://zoom.us/j/123456",
            "isRecurring": False,
        }

        mock_response.json.return_value = complete_response

        # Patch the _request method
        with patch.object(
            calendars_client, "_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            # Call create_appointment
            result = await calendars_client.create_appointment(appointment_data)

            # Verify the request was made to the correct endpoint
            mock_request.assert_called()
            call_args = mock_request.call_args

            # The endpoint should be /calendars/events/appointments
            assert call_args[0][0] == "POST"
            # Could be either endpoint due to the fallback logic
            assert call_args[0][1] in [
                "/calendars/test_calendar_id/appointments",
                "/calendars/events/appointments",
            ]

            # Verify the result
            assert isinstance(result, Appointment)
            assert result.id == "new_appointment_id"

    @pytest.mark.asyncio
    async def test_free_slots_response_parsing(self, calendars_client):
        """Test parsing of the actual free slots response format"""
        calendar_id = "test_calendar_id"
        location_id = "test_location_id"
        start_date = date(2025, 6, 10)

        # Mock the actual response format from GoHighLevel
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "2025-06-10": {
                "slots": [
                    "2025-06-10T09:00:00-05:00",
                    "2025-06-10T09:30:00-05:00",
                    "2025-06-10T10:00:00-05:00",
                ]
            },
            "2025-06-11": {
                "slots": [
                    "2025-06-11T14:00:00-05:00",
                    "2025-06-11T14:30:00-05:00",
                ]
            },
            "traceId": "test-trace-id",
        }

        with patch.object(
            calendars_client, "_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await calendars_client.get_free_slots(
                calendar_id=calendar_id, location_id=location_id, start_date=start_date
            )

            # Should parse all slots from both dates
            assert len(result.slots) == 5

            # Check slot times are preserved (as datetime objects)
            # Convert to ISO strings for comparison
            slot_times = [
                (
                    slot.startTime.isoformat()
                    if isinstance(slot.startTime, datetime)
                    else slot.startTime
                )
                for slot in result.slots
            ]
            # The timezone might be different in the datetime object, so check the date/time parts
            assert any("2025-06-10T09:00:00" in str(time) for time in slot_times)
            assert any("2025-06-11T14:30:00" in str(time) for time in slot_times)

            # Each slot should have end time 30 minutes after start
            for slot in result.slots:
                if isinstance(slot.startTime, str):
                    start_dt = datetime.fromisoformat(
                        slot.startTime.replace("Z", "+00:00")
                    )
                else:
                    start_dt = slot.startTime

                if isinstance(slot.endTime, str):
                    end_dt = datetime.fromisoformat(slot.endTime.replace("Z", "+00:00"))
                else:
                    end_dt = slot.endTime

                # Check that end time is 30 minutes after start time
                assert end_dt == start_dt + timedelta(minutes=30)
