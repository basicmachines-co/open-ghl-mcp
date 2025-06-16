"""Tests for the models.contact module."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models.contact import (
    Contact,
    ContactCreate,
    ContactUpdate,
    ContactList,
    ContactListMeta,
    ContactSearchParams,
    ContactPhone,
    ContactEmail,
    ContactAddress,
)


class TestContactPhone:
    """Test cases for ContactPhone model."""

    def test_contact_phone_creation(self):
        """Test creating a ContactPhone with all fields."""
        phone = ContactPhone(
            phone="+1234567890",
            label="Mobile",
            type="mobile"
        )
        
        assert phone.phone == "+1234567890"
        assert phone.label == "Mobile"
        assert phone.type == "mobile"

    def test_contact_phone_all_optional(self):
        """Test that all ContactPhone fields are optional."""
        phone = ContactPhone()
        
        assert phone.phone is None
        assert phone.label is None
        assert phone.type is None


class TestContactEmail:
    """Test cases for ContactEmail model."""

    def test_contact_email_creation(self):
        """Test creating a ContactEmail with all fields."""
        email = ContactEmail(
            email="test@example.com",
            label="Work"
        )
        
        assert email.email == "test@example.com"
        assert email.label == "Work"

    def test_contact_email_all_optional(self):
        """Test that all ContactEmail fields are optional."""
        email = ContactEmail()
        
        assert email.email is None
        assert email.label is None


class TestContactAddress:
    """Test cases for ContactAddress model."""

    def test_contact_address_creation(self):
        """Test creating a ContactAddress with all fields."""
        address = ContactAddress(
            address1="123 Main St",
            city="New York",
            state="NY",
            country="US",
            postalCode="10001"
        )
        
        assert address.address1 == "123 Main St"
        assert address.city == "New York"
        assert address.state == "NY"
        assert address.country == "US"
        assert address.postalCode == "10001"

    def test_contact_address_default_country(self):
        """Test that country defaults to US."""
        address = ContactAddress()
        
        assert address.country == "US"
        assert address.address1 is None
        assert address.city is None


class TestContact:
    """Test cases for Contact model."""

    def test_contact_minimal(self):
        """Test creating a Contact with minimal required fields."""
        contact = Contact(locationId="loc123")
        
        assert contact.locationId == "loc123"
        assert contact.id is None
        assert contact.firstName is None
        assert contact.tags == []
        assert contact.dnd is False
        assert contact.country == "US"

    def test_contact_full(self):
        """Test creating a Contact with all common fields."""
        now = datetime.now(timezone.utc)
        contact = Contact(
            id="contact123",
            locationId="loc123",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            tags=["customer", "vip"],
            dnd=True,
            dateAdded=now,
            dateUpdated=now,
            companyName="Acme Corp",
            address1="123 Main St",
            city="New York",
            state="NY",
            postalCode="10001",
            website="https://example.com",
            timezone="America/New_York",
            source="website",
            assignedTo="user123"
        )
        
        assert contact.id == "contact123"
        assert contact.firstName == "John"
        assert contact.lastName == "Doe"
        assert contact.email == "john@example.com"
        assert contact.phone == "+1234567890"
        assert contact.tags == ["customer", "vip"]
        assert contact.dnd is True
        assert contact.dateAdded == now
        assert contact.companyName == "Acme Corp"

    def test_contact_additional_phones(self):
        """Test Contact with additional phones."""
        phone1 = ContactPhone(phone="+1111111111", label="Home")
        phone2 = ContactPhone(phone="+2222222222", label="Work")
        
        contact = Contact(
            locationId="loc123",
            phone="+1234567890",
            additionalPhones=[phone1, phone2]
        )
        
        assert contact.phone == "+1234567890"
        assert len(contact.additionalPhones) == 2
        assert contact.additionalPhones[0].phone == "+1111111111"
        assert contact.additionalPhones[1].label == "Work"

    def test_contact_datetime_fields(self):
        """Test Contact datetime field handling."""
        now = datetime.now(timezone.utc)
        contact = Contact(
            locationId="loc123",
            dateAdded=now,
            dateUpdated=now,
            dateOfBirth=now,
            lastActivity=now,
            lastSessionActivityAt=now,
            validEmailDate=now
        )
        
        assert contact.dateAdded == now
        assert contact.dateUpdated == now
        assert contact.dateOfBirth == now
        assert contact.lastActivity == now
        assert contact.lastSessionActivityAt == now
        assert contact.validEmailDate == now

    def test_contact_list_fields_default_empty(self):
        """Test that list fields default to empty lists."""
        contact = Contact(locationId="loc123")
        
        assert contact.tags == []
        assert contact.followers == []
        assert contact.additionalEmails == []
        assert contact.attributions == []

    def test_contact_missing_location_id(self):
        """Test that locationId is required."""
        with pytest.raises(ValidationError) as exc_info:
            Contact()
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "locationId" for e in errors)


class TestContactCreate:
    """Test cases for ContactCreate model."""

    def test_contact_create_minimal(self):
        """Test creating ContactCreate with minimal fields."""
        contact = ContactCreate(locationId="loc123")
        
        assert contact.locationId == "loc123"
        assert contact.firstName is None
        assert contact.email is None
        assert contact.dnd is False

    def test_contact_create_full(self):
        """Test creating ContactCreate with all fields."""
        contact = ContactCreate(
            locationId="loc123",
            firstName="Jane",
            lastName="Smith",
            email="jane@example.com",
            phone="+9876543210",
            tags=["lead", "hot"],
            dnd=True,
            companyName="Tech Corp",
            customFields=[{"id": "field1", "value": "custom"}],
            source="api",
            timezone="America/Los_Angeles",
            website="https://techcorp.com",
            address1="456 Oak Ave",
            city="Los Angeles",
            state="CA",
            postalCode="90001"
        )
        
        assert contact.locationId == "loc123"
        assert contact.firstName == "Jane"
        assert contact.tags == ["lead", "hot"]
        assert contact.dnd is True
        assert contact.customFields == [{"id": "field1", "value": "custom"}]

    def test_contact_create_missing_location_id(self):
        """Test that locationId is required for ContactCreate."""
        with pytest.raises(ValidationError) as exc_info:
            ContactCreate(firstName="John")
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "locationId" for e in errors)


class TestContactUpdate:
    """Test cases for ContactUpdate model."""

    def test_contact_update_all_optional(self):
        """Test that all ContactUpdate fields are optional."""
        update = ContactUpdate()
        
        # Should create successfully with no fields
        assert update.firstName is None
        assert update.email is None
        assert update.tags is None

    def test_contact_update_partial(self):
        """Test updating only some fields."""
        update = ContactUpdate(
            firstName="Updated",
            tags=["updated", "tag"],
            dnd=True
        )
        
        assert update.firstName == "Updated"
        assert update.tags == ["updated", "tag"]
        assert update.dnd is True
        assert update.lastName is None  # Not updated
        assert update.email is None  # Not updated

    def test_contact_update_custom_fields(self):
        """Test updating custom fields."""
        update = ContactUpdate(
            customFields=[
                {"id": "custom1", "value": "new value"},
                {"id": "custom2", "value": 123}
            ]
        )
        
        assert len(update.customFields) == 2
        assert update.customFields[0]["value"] == "new value"


class TestContactListMeta:
    """Test cases for ContactListMeta model."""

    def test_contact_list_meta_required_fields(self):
        """Test ContactListMeta with required fields only."""
        meta = ContactListMeta(total=100)
        
        assert meta.total == 100
        assert meta.nextPageUrl is None
        assert meta.currentPage is None

    def test_contact_list_meta_full(self):
        """Test ContactListMeta with all fields."""
        meta = ContactListMeta(
            total=100,
            nextPageUrl="/contacts?page=2",
            startAfterId="contact123",
            startAfter=1234567890,
            currentPage=1,
            nextPage="2",
            prevPage="0"
        )
        
        assert meta.total == 100
        assert meta.nextPageUrl == "/contacts?page=2"
        assert meta.currentPage == 1
        assert meta.nextPage == "2"
        assert meta.prevPage == "0"


class TestContactList:
    """Test cases for ContactList model."""

    def test_contact_list_minimal(self):
        """Test ContactList with minimal fields."""
        contacts = [
            Contact(locationId="loc123", firstName="John"),
            Contact(locationId="loc123", firstName="Jane")
        ]
        
        contact_list = ContactList(
            contacts=contacts,
            count=2
        )
        
        assert len(contact_list.contacts) == 2
        assert contact_list.count == 2
        assert contact_list.total is None
        assert contact_list.meta is None

    def test_contact_list_with_meta(self):
        """Test ContactList with metadata."""
        meta = ContactListMeta(total=50, currentPage=1)
        contact_list = ContactList(
            contacts=[],
            count=0,
            total=50,
            meta=meta,
            traceId="trace123"
        )
        
        assert contact_list.contacts == []
        assert contact_list.total == 50
        assert contact_list.meta.total == 50
        assert contact_list.traceId == "trace123"


class TestContactSearchParams:
    """Test cases for ContactSearchParams model."""

    def test_search_params_minimal(self):
        """Test ContactSearchParams with minimal fields."""
        params = ContactSearchParams(locationId="loc123")
        
        assert params.locationId == "loc123"
        assert params.limit == 100  # Default
        assert params.skip == 0  # Default
        assert params.query is None

    def test_search_params_full(self):
        """Test ContactSearchParams with all fields."""
        now = datetime.now(timezone.utc)
        params = ContactSearchParams(
            locationId="loc123",
            query="john",
            limit=50,
            skip=20,
            email="john@example.com",
            phone="+1234567890",
            tags=["customer", "vip"],
            startDate=now,
            endDate=now
        )
        
        assert params.query == "john"
        assert params.limit == 50
        assert params.skip == 20
        assert params.tags == ["customer", "vip"]
        assert params.startDate == now

    def test_search_params_limit_validation(self):
        """Test that limit has proper bounds."""
        # Valid limits
        params1 = ContactSearchParams(locationId="loc123", limit=1)
        params2 = ContactSearchParams(locationId="loc123", limit=100)
        
        assert params1.limit == 1
        assert params2.limit == 100
        
        # Invalid limits
        with pytest.raises(ValidationError):
            ContactSearchParams(locationId="loc123", limit=0)
        
        with pytest.raises(ValidationError):
            ContactSearchParams(locationId="loc123", limit=101)

    def test_search_params_skip_validation(self):
        """Test that skip cannot be negative."""
        # Valid skip
        params = ContactSearchParams(locationId="loc123", skip=0)
        assert params.skip == 0
        
        # Invalid skip
        with pytest.raises(ValidationError):
            ContactSearchParams(locationId="loc123", skip=-1)