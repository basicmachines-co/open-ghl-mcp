"""Tests for forms functionality"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.models.form import (
    Form,
    FormField,
    FormList,
    FormSubmission,
    FormSubmissionList,
    FormFileUploadRequest,
)
from src.api.forms import FormsClient
from src.services.oauth import OAuthService


@pytest.fixture
def mock_oauth_service():
    """Create a mock OAuth service"""
    oauth_service = MagicMock(spec=OAuthService)
    oauth_service.get_valid_token = AsyncMock(return_value="test_token")
    oauth_service.get_location_token = AsyncMock(return_value="location_token")
    return oauth_service


@pytest.fixture
def forms_client(mock_oauth_service):
    """Create a forms client with mocked OAuth"""
    return FormsClient(mock_oauth_service)


@pytest.fixture
def sample_form():
    """Create a sample form"""
    return Form(
        id="form_123",
        name="Contact Form",
        locationId="loc_123",
        description="Test contact form",
        isActive=True,
        fields=[
            FormField(id="firstName", label="First Name", type="text", required=True),
            FormField(id="email", label="Email", type="email", required=True),
            FormField(
                id="custom_field_123",
                label="How did you hear about us?",
                type="dropdown",
                required=False,
                options=["Google", "Facebook", "Referral", "Other"],
            ),
        ],
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_submission():
    """Create a sample form submission"""
    return FormSubmission(
        id="sub_123",
        formId="form_123",
        contactId="contact_123",
        locationId="loc_123",
        data={
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "custom_field_123": "Google",
        },
        submittedAt=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_forms(forms_client, sample_form):
    """Test getting forms for a location"""
    # Mock the response
    with patch.object(forms_client, "_request") as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "forms": [sample_form.model_dump()],
            "total": 1,
            "count": 1,
        }
        mock_request.return_value = mock_response

        # Call the method
        result = await forms_client.get_forms("loc_123")

        # Assertions
        assert isinstance(result, FormList)
        assert len(result.forms) == 1
        assert result.forms[0].id == "form_123"
        mock_request.assert_called_once_with(
            "GET",
            "/forms/",
            params={"locationId": "loc_123", "limit": 100},
            location_id="loc_123",
        )


@pytest.mark.asyncio
async def test_upload_form_file(forms_client):
    """Test file upload to form field"""
    # Create file upload request
    file_upload = FormFileUploadRequest(
        contactId="contact_123",
        locationId="loc_123",
        fieldId="file_field_123",
        fileName="test.pdf",
        fileContent="VGVzdCBmaWxlIGNvbnRlbnQ=",  # Base64 encoded "Test file content"
        contentType="application/pdf",
    )

    # Mock the response
    with patch.object(forms_client, "_get_headers") as mock_headers:
        mock_headers.return_value = {"Authorization": "Bearer test_token"}

        with patch.object(forms_client.client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True, "fileId": "file_123"}
            mock_post.return_value = mock_response

            # Call the method
            result = await forms_client.upload_form_file(file_upload)

            # Assertions
            assert result["success"] is True
            assert result["fileId"] == "file_123"

            # Check the call
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            assert "files" in call_kwargs
            assert "data" in call_kwargs


@pytest.mark.asyncio
async def test_get_all_submissions(forms_client, sample_submission):
    """Test getting all form submissions"""
    # Mock the response
    with patch.object(forms_client, "_request") as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "submissions": [sample_submission.model_dump()],
            "meta": {"total": 1, "currentPage": 1, "nextPage": None, "prevPage": None},
        }
        mock_request.return_value = mock_response

        # Call the method
        result = await forms_client.get_all_submissions(
            "loc_123",
            form_id="form_123",
            start_date="2025-06-01",
            end_date="2025-06-08",
        )

        # Assertions
        assert isinstance(result, FormSubmissionList)
        assert len(result.submissions) == 1
        assert result.submissions[0].id == "sub_123"
        mock_request.assert_called_once_with(
            "GET",
            "/forms/submissions",
            params={
                "locationId": "loc_123",
                "limit": 100,
                "formId": "form_123",
                "startDate": "2025-06-01",
                "endDate": "2025-06-08",
            },
            location_id="loc_123",
        )
