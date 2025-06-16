"""Tests for the models.form module."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models.form import (
    FormField,
    FormSettings,
    Form,
    FormList,
    FormSubmissionData,
    FormSubmission,
    FormSubmissionList,
    FormSubmitRequest,
    FormSubmitResponse,
    FormFileUploadRequest,
    FormSearchParams,
    FormSubmissionSearchParams,
)


class TestFormField:
    """Test cases for FormField model."""

    def test_form_field_minimal(self):
        """Test creating FormField with minimal required fields."""
        field = FormField(
            id="firstName",
            label="First Name",
            type="text"
        )
        
        assert field.id == "firstName"
        assert field.label == "First Name"
        assert field.type == "text"
        assert field.required is False
        assert field.placeholder is None
        assert field.options is None

    def test_form_field_text_type(self):
        """Test creating text field with validation."""
        field = FormField(
            id="username",
            label="Username",
            type="text",
            required=True,
            placeholder="Enter username",
            minLength=3,
            maxLength=20,
            pattern="^[a-zA-Z0-9_]+$"
        )
        
        assert field.required is True
        assert field.placeholder == "Enter username"
        assert field.minLength == 3
        assert field.maxLength == 20
        assert field.pattern == "^[a-zA-Z0-9_]+$"

    def test_form_field_dropdown_type(self):
        """Test creating dropdown field with options."""
        field = FormField(
            id="interest",
            label="Interest Level",
            type="dropdown",
            required=True,
            options=["Low", "Medium", "High", "Very High"]
        )
        
        assert field.type == "dropdown"
        assert field.options == ["Low", "Medium", "High", "Very High"]
        assert len(field.options) == 4

    def test_form_field_various_types(self):
        """Test various field types."""
        types = ["text", "email", "phone", "textarea", "dropdown", 
                 "checkbox", "radio", "file", "date", "time", "number"]
        
        for field_type in types:
            field = FormField(
                id=f"field_{field_type}",
                label=f"Test {field_type}",
                type=field_type
            )
            assert field.type == field_type

    def test_form_field_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FormField(id="test")  # Missing label and type
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "label" in error_fields
        assert "type" in error_fields


class TestFormSettings:
    """Test cases for FormSettings model."""

    def test_form_settings_all_optional(self):
        """Test that all FormSettings fields are optional."""
        settings = FormSettings()
        
        assert settings.captchaEnabled is None
        assert settings.emailNotifications is None
        assert settings.assignToUser is None
        assert settings.redirectUrl is None
        assert settings.thankYouMessage is None

    def test_form_settings_full(self):
        """Test FormSettings with all fields."""
        settings = FormSettings(
            captchaEnabled=True,
            emailNotifications=True,
            assignToUser="user123",
            redirectUrl="https://example.com/thank-you",
            thankYouMessage="Thank you for submitting!"
        )
        
        assert settings.captchaEnabled is True
        assert settings.emailNotifications is True
        assert settings.assignToUser == "user123"
        assert settings.redirectUrl == "https://example.com/thank-you"
        assert settings.thankYouMessage == "Thank you for submitting!"


class TestForm:
    """Test cases for Form model."""

    def test_form_minimal(self):
        """Test creating Form with minimal required fields."""
        form = Form(
            id="form123",
            name="Contact Form",
            locationId="loc123"
        )
        
        assert form.id == "form123"
        assert form.name == "Contact Form"
        assert form.locationId == "loc123"
        assert form.isActive is True  # Default
        assert form.fields == []  # Default empty list
        assert form.description is None

    def test_form_with_fields(self):
        """Test Form with multiple fields."""
        fields = [
            FormField(id="firstName", label="First Name", type="text", required=True),
            FormField(id="lastName", label="Last Name", type="text", required=True),
            FormField(id="email", label="Email", type="email", required=True),
            FormField(id="phone", label="Phone", type="phone"),
            FormField(id="interest", label="Interest", type="dropdown", 
                     options=["Sales", "Support", "Other"])
        ]
        
        form = Form(
            id="form123",
            name="Lead Generation Form",
            locationId="loc123",
            description="Capture new leads",
            fields=fields
        )
        
        assert len(form.fields) == 5
        assert form.fields[0].id == "firstName"
        assert form.fields[2].type == "email"
        assert form.fields[4].options == ["Sales", "Support", "Other"]

    def test_form_with_settings(self):
        """Test Form with settings configuration."""
        settings = FormSettings(
            captchaEnabled=True,
            emailNotifications=True,
            assignToUser="user456"
        )
        
        form = Form(
            id="form123",
            name="Secure Form",
            locationId="loc123",
            settings=settings,
            thankYouMessage="Thanks for your submission!",
            redirectUrl="https://example.com/success"
        )
        
        assert form.settings.captchaEnabled is True
        assert form.thankYouMessage == "Thanks for your submission!"
        assert form.redirectUrl == "https://example.com/success"

    def test_form_with_timestamps(self):
        """Test Form with datetime fields."""
        now = datetime.now(timezone.utc)
        
        form = Form(
            id="form123",
            name="Timestamped Form",
            locationId="loc123",
            createdAt=now,
            updatedAt=now
        )
        
        assert form.createdAt == now
        assert form.updatedAt == now

    def test_form_inactive(self):
        """Test creating inactive form."""
        form = Form(
            id="form123",
            name="Inactive Form",
            locationId="loc123",
            isActive=False
        )
        
        assert form.isActive is False

    def test_form_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Form(id="form123", name="Test")  # Missing locationId
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "locationId" for e in errors)


class TestFormList:
    """Test cases for FormList model."""

    def test_form_list_minimal(self):
        """Test FormList with minimal fields."""
        forms = [
            Form(id="form1", name="Form 1", locationId="loc123"),
            Form(id="form2", name="Form 2", locationId="loc123")
        ]
        
        form_list = FormList(forms=forms)
        
        assert len(form_list.forms) == 2
        assert form_list.total is None
        assert form_list.count is None

    def test_form_list_with_pagination(self):
        """Test FormList with pagination info."""
        form_list = FormList(
            forms=[],
            total=50,
            count=10
        )
        
        assert form_list.forms == []
        assert form_list.total == 50
        assert form_list.count == 10


class TestFormSubmissionData:
    """Test cases for FormSubmissionData model."""

    def test_form_submission_data_all_optional(self):
        """Test that all standard fields are optional."""
        data = FormSubmissionData()
        
        assert data.firstName is None
        assert data.lastName is None
        assert data.email is None
        assert data.phone is None
        assert data.company is None
        assert data.message is None

    def test_form_submission_data_standard_fields(self):
        """Test FormSubmissionData with standard fields."""
        data = FormSubmissionData(
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            company="Acme Corp",
            message="I'm interested in your services"
        )
        
        assert data.firstName == "John"
        assert data.lastName == "Doe"
        assert data.email == "john@example.com"
        assert data.phone == "+1234567890"
        assert data.company == "Acme Corp"
        assert data.message == "I'm interested in your services"

    def test_form_submission_data_extra_fields(self):
        """Test FormSubmissionData with custom fields."""
        data = FormSubmissionData(
            firstName="Jane",
            email="jane@example.com",
            custom_field_abc123="High Priority",
            another_custom_field="Custom Value",
            numeric_field=42
        )
        
        assert data.firstName == "Jane"
        assert data.custom_field_abc123 == "High Priority"  # type: ignore
        assert data.another_custom_field == "Custom Value"  # type: ignore
        assert data.numeric_field == 42  # type: ignore


class TestFormSubmission:
    """Test cases for FormSubmission model."""

    def test_form_submission_minimal(self):
        """Test FormSubmission with minimal required fields."""
        now = datetime.now(timezone.utc)
        
        submission = FormSubmission(
            id="sub123",
            formId="form123",
            contactId="contact123",
            locationId="loc123",
            data={"firstName": "John", "email": "john@example.com"},
            submittedAt=now
        )
        
        assert submission.id == "sub123"
        assert submission.formId == "form123"
        assert submission.contactId == "contact123"
        assert submission.data == {"firstName": "John", "email": "john@example.com"}
        assert submission.submittedAt == now
        assert submission.ipAddress is None

    def test_form_submission_full(self):
        """Test FormSubmission with all fields."""
        now = datetime.now(timezone.utc)
        data = {
            "firstName": "Jane",
            "lastName": "Smith",
            "email": "jane@example.com",
            "custom_field": "Custom Value"
        }
        
        submission = FormSubmission(
            id="sub456",
            formId="form456",
            contactId="contact456",
            locationId="loc456",
            data=data,
            ipAddress="192.168.1.1",
            userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            submittedAt=now,
            attributionSource="google_ads",
            lastAttributionSource="facebook"
        )
        
        assert submission.ipAddress == "192.168.1.1"
        assert submission.userAgent.startswith("Mozilla/5.0")
        assert submission.attributionSource == "google_ads"
        assert submission.lastAttributionSource == "facebook"
        assert submission.data["custom_field"] == "Custom Value"

    def test_form_submission_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FormSubmission(
                id="sub123",
                formId="form123"
                # Missing contactId, locationId, data, submittedAt
            )
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "contactId" in error_fields
        assert "locationId" in error_fields
        assert "data" in error_fields
        assert "submittedAt" in error_fields


class TestFormSubmissionList:
    """Test cases for FormSubmissionList model."""

    def test_form_submission_list_minimal(self):
        """Test FormSubmissionList with minimal fields."""
        now = datetime.now(timezone.utc)
        submissions = [
            FormSubmission(
                id="sub1",
                formId="form123",
                contactId="contact1",
                locationId="loc123",
                data={"email": "test1@example.com"},
                submittedAt=now
            ),
            FormSubmission(
                id="sub2",
                formId="form123",
                contactId="contact2",
                locationId="loc123",
                data={"email": "test2@example.com"},
                submittedAt=now
            )
        ]
        
        sub_list = FormSubmissionList(submissions=submissions)
        
        assert len(sub_list.submissions) == 2
        assert sub_list.total is None
        assert sub_list.count is None

    def test_form_submission_list_with_pagination(self):
        """Test FormSubmissionList with pagination."""
        sub_list = FormSubmissionList(
            submissions=[],
            total=100,
            count=20
        )
        
        assert sub_list.submissions == []
        assert sub_list.total == 100
        assert sub_list.count == 20


class TestFormSubmitRequest:
    """Test cases for FormSubmitRequest model."""

    def test_form_submit_request_minimal(self):
        """Test FormSubmitRequest with minimal required fields."""
        request = FormSubmitRequest(
            formId="form123",
            locationId="loc123"
        )
        
        assert request.formId == "form123"
        assert request.locationId == "loc123"
        assert request.customFields == {}

    def test_form_submit_request_standard_fields(self):
        """Test FormSubmitRequest with standard fields."""
        request = FormSubmitRequest(
            formId="form123",
            locationId="loc123",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            company="Tech Corp",
            message="Interested in demo"
        )
        
        assert request.firstName == "John"
        assert request.lastName == "Doe"
        assert request.email == "john@example.com"
        assert request.phone == "+1234567890"
        assert request.company == "Tech Corp"
        assert request.message == "Interested in demo"

    def test_form_submit_request_with_custom_fields(self):
        """Test FormSubmitRequest with custom fields."""
        custom_fields = {
            "interest_level": "High",
            "budget": "$10,000",
            "timeline": "Q1 2024"
        }
        
        request = FormSubmitRequest(
            formId="form123",
            locationId="loc123",
            firstName="Jane",
            email="jane@example.com",
            customFields=custom_fields
        )
        
        assert request.customFields == custom_fields
        assert request.customFields["interest_level"] == "High"

    def test_form_submit_request_to_form_data(self):
        """Test to_form_data method."""
        request = FormSubmitRequest(
            formId="form123",
            locationId="loc123",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            customFields={"source": "website", "priority": "high"}
        )
        
        data = request.to_form_data()
        
        assert data["formId"] == "form123"
        assert data["locationId"] == "loc123"
        assert data["firstName"] == "John"
        assert data["lastName"] == "Doe"
        assert data["email"] == "john@example.com"
        assert data["source"] == "website"
        assert data["priority"] == "high"
        assert "phone" not in data  # Not provided
        assert "customFields" not in data  # Flattened

    def test_form_submit_request_to_form_data_minimal(self):
        """Test to_form_data with minimal fields."""
        request = FormSubmitRequest(
            formId="form123",
            locationId="loc123"
        )
        
        data = request.to_form_data()
        
        assert data == {"formId": "form123", "locationId": "loc123"}

    def test_form_submit_request_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FormSubmitRequest(formId="form123")  # Missing locationId
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "locationId" for e in errors)


class TestFormSubmitResponse:
    """Test cases for FormSubmitResponse model."""

    def test_form_submit_response_success(self):
        """Test successful form submission response."""
        response = FormSubmitResponse(
            success=True,
            submissionId="sub123",
            contactId="contact123",
            message="Form submitted successfully",
            redirectUrl="https://example.com/thank-you"
        )
        
        assert response.success is True
        assert response.submissionId == "sub123"
        assert response.contactId == "contact123"
        assert response.message == "Form submitted successfully"
        assert response.redirectUrl == "https://example.com/thank-you"

    def test_form_submit_response_failure(self):
        """Test failed form submission response."""
        response = FormSubmitResponse(
            success=False,
            message="Invalid email address"
        )
        
        assert response.success is False
        assert response.message == "Invalid email address"
        assert response.submissionId is None
        assert response.contactId is None
        assert response.redirectUrl is None

    def test_form_submit_response_minimal(self):
        """Test FormSubmitResponse with minimal fields."""
        response = FormSubmitResponse(success=True)
        
        assert response.success is True
        assert response.submissionId is None
        assert response.contactId is None
        assert response.message is None

    def test_form_submit_response_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FormSubmitResponse()  # Missing success field
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "success" for e in errors)


class TestFormFileUploadRequest:
    """Test cases for FormFileUploadRequest model."""

    def test_form_file_upload_request_minimal(self):
        """Test FormFileUploadRequest with required fields."""
        request = FormFileUploadRequest(
            contactId="contact123",
            locationId="loc123",
            fieldId="field_upload",
            fileName="document.pdf",
            fileContent="SGVsbG8gV29ybGQh"  # Base64 encoded "Hello World!"
        )
        
        assert request.contactId == "contact123"
        assert request.locationId == "loc123"
        assert request.fieldId == "field_upload"
        assert request.fileName == "document.pdf"
        assert request.fileContent == "SGVsbG8gV29ybGQh"
        assert request.contentType == "application/octet-stream"  # Default

    def test_form_file_upload_request_with_content_type(self):
        """Test FormFileUploadRequest with custom content type."""
        request = FormFileUploadRequest(
            contactId="contact123",
            locationId="loc123",
            fieldId="field_image",
            fileName="photo.jpg",
            fileContent="base64imagedata",
            contentType="image/jpeg"
        )
        
        assert request.contentType == "image/jpeg"

    def test_form_file_upload_request_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FormFileUploadRequest(
                contactId="contact123",
                locationId="loc123"
                # Missing fieldId, fileName, fileContent
            )
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "fieldId" in error_fields
        assert "fileName" in error_fields
        assert "fileContent" in error_fields


class TestFormSearchParams:
    """Test cases for FormSearchParams model."""

    def test_form_search_params_minimal(self):
        """Test FormSearchParams with minimal fields."""
        params = FormSearchParams(locationId="loc123")
        
        assert params.locationId == "loc123"
        assert params.limit == 100  # Default
        assert params.skip == 0  # Default

    def test_form_search_params_with_pagination(self):
        """Test FormSearchParams with pagination."""
        params = FormSearchParams(
            locationId="loc123",
            limit=50,
            skip=20
        )
        
        assert params.limit == 50
        assert params.skip == 20

    def test_form_search_params_limit_validation(self):
        """Test limit bounds validation."""
        # Valid limits
        params1 = FormSearchParams(locationId="loc123", limit=1)
        params2 = FormSearchParams(locationId="loc123", limit=100)
        
        assert params1.limit == 1
        assert params2.limit == 100
        
        # Invalid limits
        with pytest.raises(ValidationError):
            FormSearchParams(locationId="loc123", limit=0)
        
        with pytest.raises(ValidationError):
            FormSearchParams(locationId="loc123", limit=101)

    def test_form_search_params_skip_validation(self):
        """Test skip non-negative validation."""
        # Valid skip
        params = FormSearchParams(locationId="loc123", skip=0)
        assert params.skip == 0
        
        # Invalid skip
        with pytest.raises(ValidationError):
            FormSearchParams(locationId="loc123", skip=-1)


class TestFormSubmissionSearchParams:
    """Test cases for FormSubmissionSearchParams model."""

    def test_form_submission_search_params_minimal(self):
        """Test FormSubmissionSearchParams with minimal fields."""
        params = FormSubmissionSearchParams(locationId="loc123")
        
        assert params.locationId == "loc123"
        assert params.formId is None
        assert params.contactId is None
        assert params.startDate is None
        assert params.endDate is None
        assert params.limit == 100
        assert params.skip == 0
        assert params.page is None

    def test_form_submission_search_params_full(self):
        """Test FormSubmissionSearchParams with all fields."""
        params = FormSubmissionSearchParams(
            locationId="loc123",
            formId="form123",
            contactId="contact123",
            startDate="2024-01-01",
            endDate="2024-12-31",
            limit=50,
            skip=100,
            page=3
        )
        
        assert params.formId == "form123"
        assert params.contactId == "contact123"
        assert params.startDate == "2024-01-01"
        assert params.endDate == "2024-12-31"
        assert params.limit == 50
        assert params.skip == 100
        assert params.page == 3

    def test_form_submission_search_params_date_format(self):
        """Test date format for search params."""
        params = FormSubmissionSearchParams(
            locationId="loc123",
            startDate="2024-06-01",
            endDate="2024-06-30"
        )
        
        # Dates should be strings in YYYY-MM-DD format
        assert isinstance(params.startDate, str)
        assert isinstance(params.endDate, str)
        assert params.startDate == "2024-06-01"
        assert params.endDate == "2024-06-30"

    def test_form_submission_search_params_validation(self):
        """Test validation for search params."""
        # Valid params
        params = FormSubmissionSearchParams(
            locationId="loc123",
            limit=1,
            skip=0
        )
        assert params.limit == 1
        
        # Invalid limit
        with pytest.raises(ValidationError):
            FormSubmissionSearchParams(locationId="loc123", limit=0)
        
        # Invalid skip
        with pytest.raises(ValidationError):
            FormSubmissionSearchParams(locationId="loc123", skip=-1)