"""Tests for the models.calendar module."""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from src.models.calendar import (
    AppointmentStatus,
    MeetingLocationType,
    CalendarType,
    AppointmentCreate,
    AppointmentUpdate,
    Appointment,
    Calendar,
    AppointmentList,
    CalendarList,
    FreeSlot,
    FreeSlotsResult,
)


class TestAppointmentStatus:
    """Test cases for AppointmentStatus enum."""

    def test_appointment_status_values(self):
        """Test all appointment status values."""
        assert AppointmentStatus.CONFIRMED.value == "confirmed"
        assert AppointmentStatus.CANCELLED.value == "cancelled"
        assert AppointmentStatus.SHOWED.value == "showed"
        assert AppointmentStatus.NO_SHOW.value == "no_show"
        assert AppointmentStatus.INVALID.value == "invalid"


class TestMeetingLocationType:
    """Test cases for MeetingLocationType enum."""

    def test_meeting_location_type_values(self):
        """Test all meeting location type values."""
        assert MeetingLocationType.PHYSICAL.value == "physical"
        assert MeetingLocationType.PHONE.value == "phone"
        assert MeetingLocationType.ZOOM.value == "zoom"
        assert MeetingLocationType.GOOGLE_MEET.value == "google_meet"
        assert MeetingLocationType.CUSTOM.value == "custom"


class TestCalendarType:
    """Test cases for CalendarType enum."""

    def test_calendar_type_values(self):
        """Test all calendar type values."""
        assert CalendarType.ROUND_ROBIN.value == "round_robin"
        assert CalendarType.INDIVIDUAL.value == "individual"
        assert CalendarType.COLLECTIVE.value == "collective"


class TestAppointmentCreate:
    """Test cases for AppointmentCreate model."""

    def test_appointment_create_minimal(self):
        """Test creating AppointmentCreate with minimal required fields."""
        start_time = datetime.now(timezone.utc)
        
        appt = AppointmentCreate(
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime=start_time
        )
        
        assert appt.calendarId == "cal123"
        assert appt.locationId == "loc123"
        assert appt.contactId == "contact123"
        assert appt.startTime == start_time
        assert appt.endTime is None
        assert appt.appointmentStatus == AppointmentStatus.CONFIRMED  # Default

    def test_appointment_create_with_string_datetime(self):
        """Test creating AppointmentCreate with ISO string datetime."""
        iso_string = "2025-06-09T11:00:00-05:00"
        
        appt = AppointmentCreate(
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime=iso_string
        )
        
        # Validator should parse it to datetime
        assert isinstance(appt.startTime, datetime)
        assert appt.startTime.hour == 11

    def test_appointment_create_with_z_datetime(self):
        """Test creating AppointmentCreate with Z suffix datetime."""
        z_string = "2025-06-09T16:00:00Z"
        
        appt = AppointmentCreate(
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime=z_string,
            endTime="2025-06-09T16:30:00Z"
        )
        
        assert isinstance(appt.startTime, datetime)
        assert isinstance(appt.endTime, datetime)
        assert appt.startTime.tzinfo is not None

    def test_appointment_create_full(self):
        """Test creating AppointmentCreate with all fields."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)
        
        appt = AppointmentCreate(
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime=start,
            endTime=end,
            title="Strategy Session",
            meetingLocationType=MeetingLocationType.ZOOM,
            appointmentStatus=AppointmentStatus.CONFIRMED,
            assignedUserId="user123",
            notes="Important meeting about project X",
            address="123 Main St, Suite 100",
            ignoreDateRange=False,
            toNotify=True
        )
        
        assert appt.title == "Strategy Session"
        assert appt.meetingLocationType == MeetingLocationType.ZOOM
        assert appt.assignedUserId == "user123"
        assert appt.notes == "Important meeting about project X"
        assert appt.toNotify is True

    def test_appointment_create_invalid_datetime(self):
        """Test that invalid datetime strings are handled."""
        with pytest.raises(ValidationError) as exc_info:
            AppointmentCreate(
                calendarId="cal123",
                locationId="loc123",
                contactId="contact123",
                startTime="invalid-datetime"
            )
        
        # Invalid datetime should cause validation error since startTime is required
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "startTime" for e in errors)

    def test_appointment_create_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AppointmentCreate(
                calendarId="cal123",
                locationId="loc123"
                # Missing contactId and startTime
            )
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "contactId" in error_fields
        assert "startTime" in error_fields


class TestAppointmentUpdate:
    """Test cases for AppointmentUpdate model."""

    def test_appointment_update_all_optional(self):
        """Test that all AppointmentUpdate fields are optional."""
        update = AppointmentUpdate()
        
        assert update.startTime is None
        assert update.endTime is None
        assert update.title is None
        assert update.appointmentStatus is None

    def test_appointment_update_partial(self):
        """Test updating only some fields."""
        new_start = datetime.now(timezone.utc) + timedelta(days=1)
        
        update = AppointmentUpdate(
            startTime=new_start,
            title="Updated Title",
            appointmentStatus=AppointmentStatus.CANCELLED
        )
        
        assert update.startTime == new_start
        assert update.title == "Updated Title"
        assert update.appointmentStatus == AppointmentStatus.CANCELLED
        assert update.endTime is None  # Not updated

    def test_appointment_update_datetime_parsing(self):
        """Test AppointmentUpdate datetime parsing."""
        update = AppointmentUpdate(
            startTime="2025-06-10T10:00:00Z",
            endTime="2025-06-10T11:00:00Z"
        )
        
        assert isinstance(update.startTime, datetime)
        assert isinstance(update.endTime, datetime)

    def test_appointment_update_meeting_details(self):
        """Test updating meeting details."""
        update = AppointmentUpdate(
            meetingLocationType=MeetingLocationType.PHYSICAL,
            address="456 Oak Ave, Conference Room B",
            notes="Please bring the quarterly reports",
            toNotify=False
        )
        
        assert update.meetingLocationType == MeetingLocationType.PHYSICAL
        assert update.address == "456 Oak Ave, Conference Room B"
        assert update.toNotify is False


class TestAppointment:
    """Test cases for Appointment model."""

    def test_appointment_minimal(self):
        """Test creating Appointment with minimal required fields."""
        start = datetime.now(timezone.utc)
        
        appt = Appointment(
            id="appt123",
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime=start,
            appointmentStatus=AppointmentStatus.CONFIRMED
        )
        
        assert appt.id == "appt123"
        assert appt.calendarId == "cal123"
        assert appt.startTime == start
        assert appt.appointmentStatus == AppointmentStatus.CONFIRMED
        assert appt.endTime is None
        assert appt.title is None

    def test_appointment_with_string_datetimes(self):
        """Test Appointment with string datetime values."""
        appt = Appointment(
            id="appt123",
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime="2025-06-09T11:00:00-05:00",
            endTime="2025-06-09T11:30:00-05:00",
            appointmentStatus=AppointmentStatus.CONFIRMED,
            createdAt="2025-06-01T10:00:00Z",
            updatedAt="2025-06-02T10:00:00Z"
        )
        
        # Validators should parse them
        assert isinstance(appt.startTime, datetime)
        assert isinstance(appt.endTime, datetime)
        assert isinstance(appt.createdAt, datetime)
        assert isinstance(appt.updatedAt, datetime)

    def test_appointment_full(self):
        """Test creating Appointment with all common fields."""
        now = datetime.now(timezone.utc)
        start = now + timedelta(days=1)
        end = start + timedelta(hours=2)
        
        appt = Appointment(
            id="appt123",
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime=start,
            endTime=end,
            title="Project Kickoff Meeting",
            meetingLocationType=MeetingLocationType.GOOGLE_MEET,
            appointmentStatus=AppointmentStatus.CONFIRMED,
            assignedUserId="user456",
            notes="Discuss project timeline and deliverables",
            address="Virtual - Google Meet",
            dateAdded=now,
            dateUpdated=now,
            createdAt=now,
            updatedAt=now,
            calendarEventId="gcal_event_123",
            ignoreDateRange=False,
            toNotify=True
        )
        
        assert appt.title == "Project Kickoff Meeting"
        assert appt.meetingLocationType == MeetingLocationType.GOOGLE_MEET
        assert appt.assignedUserId == "user456"
        assert appt.dateAdded == now
        assert appt.calendarEventId == "gcal_event_123"

    def test_appointment_legacy_timestamp_aliases(self):
        """Test that both dateAdded/dateUpdated and createdAt/updatedAt work."""
        now = datetime.now(timezone.utc)
        
        # Using createdAt/updatedAt (which are aliased to dateAdded/dateUpdated)
        appt1 = Appointment(
            id="appt1",
            calendarId="cal123",
            locationId="loc123",
            contactId="contact123",
            startTime=now,
            appointmentStatus=AppointmentStatus.CONFIRMED,
            createdAt=now,
            updatedAt=now
        )
        
        # Due to aliases, these values should be accessible via dateAdded/dateUpdated
        assert appt1.dateAdded == now
        assert appt1.dateUpdated == now

    def test_appointment_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Appointment(
                id="appt123",
                calendarId="cal123"
                # Missing locationId, contactId, startTime, appointmentStatus
            )
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "locationId" in error_fields
        assert "contactId" in error_fields
        assert "startTime" in error_fields
        assert "appointmentStatus" in error_fields


class TestCalendar:
    """Test cases for Calendar model."""

    def test_calendar_minimal(self):
        """Test creating Calendar with minimal required fields."""
        calendar = Calendar(
            id="cal123",
            name="Sales Meetings",
            locationId="loc123"
        )
        
        assert calendar.id == "cal123"
        assert calendar.name == "Sales Meetings"
        assert calendar.locationId == "loc123"
        # Check defaults
        assert calendar.teamMembers == []
        assert calendar.openHours == []
        assert calendar.availabilities == []
        assert calendar.notifications == []

    def test_calendar_with_type_and_config(self):
        """Test Calendar with type and basic configuration."""
        calendar = Calendar(
            id="cal123",
            name="Team Standup",
            locationId="loc123",
            calendarType="round_robin",
            eventType="meeting",
            eventTitle="Daily Standup - {{contact.name}}",
            eventColor="#4285F4",
            description="Daily team synchronization meeting",
            slug="team-standup",
            widgetSlug="widget-team-standup"
        )
        
        assert calendar.calendarType == "round_robin"
        assert calendar.eventType == "meeting"
        assert calendar.eventTitle == "Daily Standup - {{contact.name}}"
        assert calendar.eventColor == "#4285F4"

    def test_calendar_slot_configuration(self):
        """Test Calendar slot and timing configuration."""
        calendar = Calendar(
            id="cal123",
            name="Consultations",
            locationId="loc123",
            slotDuration=30,
            slotDurationUnit="mins",
            slotInterval=15,
            slotIntervalUnit="mins",
            slotBuffer=10,
            slotBufferUnit="mins",
            appoinmentPerSlot=1,  # Using the aliased field name (with typo)
            appoinmentPerDay=8    # Using the aliased field name (with typo)
        )
        
        assert calendar.slotDuration == 30
        assert calendar.slotDurationUnit == "mins"
        assert calendar.slotInterval == 15
        assert calendar.appointmentPerSlot == 1  # Accessing via correct field name
        assert calendar.appointmentPerDay == 8    # Accessing via correct field name

    def test_calendar_booking_configuration(self):
        """Test Calendar booking settings."""
        calendar = Calendar(
            id="cal123",
            name="Support Calls",
            locationId="loc123",
            isActive=True,
            autoConfirm=True,
            stickyContact=False,
            allowReschedule=True,
            allowCancellation=True,
            allowBookingAfter=1,
            allowBookingAfterUnit="hours",
            allowBookingFor=30,
            allowBookingForUnit="days"
        )
        
        assert calendar.isActive is True
        assert calendar.autoConfirm is True
        assert calendar.allowReschedule is True
        assert calendar.allowBookingAfter == 1
        assert calendar.allowBookingForUnit == "days"

    def test_calendar_team_configuration(self):
        """Test Calendar team and assignment settings."""
        calendar = Calendar(
            id="cal123",
            name="Sales Demos",
            locationId="loc123",
            shouldAssignContactToTeamMember=True,
            shouldSkipAssigningContactForExisting=False,
            shouldSendAlertEmailsToAssignedMember=True,
            googleInvitationEmails=True,
            groupId="group123"
        )
        
        assert calendar.shouldAssignContactToTeamMember is True
        assert calendar.shouldSendAlertEmailsToAssignedMember is True
        assert calendar.googleInvitationEmails is True
        assert calendar.groupId == "group123"

    def test_calendar_form_configuration(self):
        """Test Calendar form and submission settings."""
        calendar = Calendar(
            id="cal123",
            name="Discovery Calls",
            locationId="loc123",
            formId="form123",
            formSubmitType="redirect",
            formSubmitRedirectUrl="https://example.com/thank-you",
            formSubmitThanksMessage="Thank you for booking!",
            guestType="required",
            consentLabel="I agree to the terms and conditions"
        )
        
        assert calendar.formId == "form123"
        assert calendar.formSubmitType == "redirect"
        assert calendar.formSubmitRedirectUrl == "https://example.com/thank-you"
        assert calendar.guestType == "required"

    def test_calendar_with_complex_objects(self):
        """Test Calendar with complex nested objects."""
        team_members = [
            {"userId": "user1", "priority": 1},
            {"userId": "user2", "priority": 2}
        ]
        open_hours = [
            {"day": "monday", "start": "09:00", "end": "17:00"},
            {"day": "tuesday", "start": "09:00", "end": "17:00"}
        ]
        notifications = [
            {"type": "email", "timing": "1_hour_before"}
        ]
        
        calendar = Calendar(
            id="cal123",
            name="Customer Success",
            locationId="loc123",
            teamMembers=team_members,
            openHours=open_hours,
            notifications=notifications,
            recurring={"enabled": True, "maxOccurrences": 10},
            lookBusyConfig={"enabled": True, "calendars": ["gcal1", "gcal2"]}
        )
        
        assert len(calendar.teamMembers) == 2
        assert calendar.teamMembers[0]["userId"] == "user1"
        assert len(calendar.openHours) == 2
        assert calendar.recurring["enabled"] is True

    def test_calendar_datetime_parsing(self):
        """Test Calendar datetime field parsing."""
        calendar = Calendar(
            id="cal123",
            name="Appointments",
            locationId="loc123",
            createdAt="2025-06-01T10:00:00Z",
            updatedAt="2025-06-02T15:30:00Z"
        )
        
        assert isinstance(calendar.createdAt, datetime)
        assert isinstance(calendar.updatedAt, datetime)

    def test_calendar_appointment_per_day_flexibility(self):
        """Test that appointmentPerDay can be int or string."""
        # With integer (using the aliased field)
        cal1 = Calendar(
            id="cal1",
            name="Calendar 1",
            locationId="loc123",
            appoinmentPerDay=10  # Using the aliased field name (with typo)
        )
        assert cal1.appointmentPerDay == 10
        
        # With string (API might return this)
        cal2 = Calendar(
            id="cal2",
            name="Calendar 2",
            locationId="loc123",
            appoinmentPerDay="unlimited"  # Using the aliased field name (with typo)
        )
        assert cal2.appointmentPerDay == "unlimited"

    def test_calendar_alias_fields(self):
        """Test Calendar fields with aliases."""
        # Using the misspelled field names (as they appear in API)
        calendar = Calendar(
            id="cal123",
            name="Test Calendar",
            locationId="loc123",
            appoinmentPerSlot=2,  # Note the typo
            appoinmentPerDay=5    # Note the typo
        )
        
        # Should be accessible via the alias
        assert calendar.appointmentPerSlot == 2
        assert calendar.appointmentPerDay == 5

    def test_calendar_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Calendar(id="cal123", name="Test")  # Missing locationId
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "locationId" for e in errors)


class TestAppointmentList:
    """Test cases for AppointmentList model."""

    def test_appointment_list_minimal(self):
        """Test AppointmentList with minimal fields."""
        appointments = [
            Appointment(
                id="appt1",
                calendarId="cal123",
                locationId="loc123",
                contactId="contact1",
                startTime=datetime.now(timezone.utc),
                appointmentStatus=AppointmentStatus.CONFIRMED
            ),
            Appointment(
                id="appt2",
                calendarId="cal123",
                locationId="loc123",
                contactId="contact2",
                startTime=datetime.now(timezone.utc),
                appointmentStatus=AppointmentStatus.CONFIRMED
            )
        ]
        
        appt_list = AppointmentList(
            appointments=appointments,
            count=2
        )
        
        assert len(appt_list.appointments) == 2
        assert appt_list.count == 2
        assert appt_list.total is None

    def test_appointment_list_with_total(self):
        """Test AppointmentList with total field."""
        appt_list = AppointmentList(
            appointments=[],
            count=0,
            total=50
        )
        
        assert appt_list.appointments == []
        assert appt_list.count == 0
        assert appt_list.total == 50

    def test_appointment_list_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AppointmentList(appointments=[])  # Missing count
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "count" for e in errors)


class TestCalendarList:
    """Test cases for CalendarList model."""

    def test_calendar_list_minimal(self):
        """Test CalendarList with minimal fields."""
        calendars = [
            Calendar(id="cal1", name="Calendar 1", locationId="loc123"),
            Calendar(id="cal2", name="Calendar 2", locationId="loc123")
        ]
        
        cal_list = CalendarList(
            calendars=calendars,
            count=2
        )
        
        assert len(cal_list.calendars) == 2
        assert cal_list.count == 2
        assert cal_list.total is None

    def test_calendar_list_empty(self):
        """Test CalendarList with no calendars."""
        cal_list = CalendarList(
            calendars=[],
            count=0,
            total=0
        )
        
        assert cal_list.calendars == []
        assert cal_list.count == 0
        assert cal_list.total == 0


class TestFreeSlot:
    """Test cases for FreeSlot model."""

    def test_free_slot_with_datetime(self):
        """Test FreeSlot with datetime objects."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(minutes=30)
        
        slot = FreeSlot(
            startTime=start,
            endTime=end,
            available=True
        )
        
        assert slot.startTime == start
        assert slot.endTime == end
        assert slot.available is True

    def test_free_slot_with_strings(self):
        """Test FreeSlot with ISO string datetimes."""
        slot = FreeSlot(
            startTime="2025-06-09T10:00:00Z",
            endTime="2025-06-09T10:30:00Z",
            available=False
        )
        
        assert isinstance(slot.startTime, datetime)
        assert isinstance(slot.endTime, datetime)
        assert slot.available is False

    def test_free_slot_datetime_parsing_variants(self):
        """Test FreeSlot with various datetime formats."""
        # With timezone offset
        slot1 = FreeSlot(
            startTime="2025-06-09T10:00:00-05:00",
            endTime="2025-06-09T10:30:00-05:00",
            available=True
        )
        assert isinstance(slot1.startTime, datetime)
        
        # With Z suffix
        slot2 = FreeSlot(
            startTime="2025-06-09T15:00:00Z",
            endTime="2025-06-09T15:30:00Z",
            available=True
        )
        assert isinstance(slot2.startTime, datetime)

    def test_free_slot_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FreeSlot(startTime="2025-06-09T10:00:00Z")  # Missing endTime and available
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "endTime" in error_fields
        assert "available" in error_fields


class TestFreeSlotsResult:
    """Test cases for FreeSlotsResult model."""

    def test_free_slots_result_minimal(self):
        """Test FreeSlotsResult with minimal fields."""
        result = FreeSlotsResult(
            slots=[],
            date="2025-06-09"
        )
        
        assert result.slots == []
        assert result.date == "2025-06-09"
        assert result.timezone is None

    def test_free_slots_result_with_slots(self):
        """Test FreeSlotsResult with multiple slots."""
        slots = [
            FreeSlot(
                startTime="2025-06-09T10:00:00Z",
                endTime="2025-06-09T10:30:00Z",
                available=True
            ),
            FreeSlot(
                startTime="2025-06-09T10:30:00Z",
                endTime="2025-06-09T11:00:00Z",
                available=True
            ),
            FreeSlot(
                startTime="2025-06-09T11:00:00Z",
                endTime="2025-06-09T11:30:00Z",
                available=False
            )
        ]
        
        result = FreeSlotsResult(
            slots=slots,
            date="2025-06-09",
            timezone="America/New_York"
        )
        
        assert len(result.slots) == 3
        assert result.slots[0].available is True
        assert result.slots[2].available is False
        assert result.timezone == "America/New_York"

    def test_free_slots_result_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FreeSlotsResult(slots=[])  # Missing date
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "date" for e in errors)