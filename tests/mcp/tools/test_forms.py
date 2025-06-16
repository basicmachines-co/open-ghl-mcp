"""Tests for the mcp.tools.forms module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.models.form import (
    Form,
    FormList,
    FormSubmission,
    FormSubmissionList,
    FormFileUploadRequest
)
from src.mcp.params.forms import (
    GetFormsParams,
    GetAllSubmissionsParams,
    UploadFormFileParams,
)
from src.mcp.tools.forms import _register_form_tools


class TestFormTools:
    """Test cases for form tools."""

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
        """Set up form tools with mocks."""
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
        _register_form_tools(mock_mcp, get_client_func)
        
        return tools, mock_client

    @pytest.mark.asyncio
    async def test_get_forms(self, setup_tools):
        """Test get_forms tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_forms = [
            Form(
                id="form1",
                name="Contact Form",
                locationId="loc123"
            ),
            Form(
                id="form2",
                name="Lead Capture Form",
                locationId="loc123"
            )
        ]
        mock_result = FormList(forms=mock_forms, count=2, total=5)
        mock_client.get_forms.return_value = mock_result
        
        # Create params
        params = GetFormsParams(
            location_id="loc123",
            limit=10,
            skip=0,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_forms"](params)
        
        # Verify
        assert result["success"] is True
        assert len(result["forms"]) == 2
        assert result["count"] == 2
        assert result["total"] == 5
        assert result["forms"][0]["id"] == "form1"
        assert result["forms"][0]["name"] == "Contact Form"
        assert result["forms"][1]["id"] == "form2"
        mock_client.get_forms.assert_called_once_with(
            location_id="loc123",
            limit=10,
            skip=0
        )

    @pytest.mark.asyncio
    async def test_get_forms_with_pagination(self, setup_tools):
        """Test get_forms with pagination."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_forms = [Form(id=f"form{i}", name=f"Form {i}", locationId="loc123") for i in range(3, 8)]
        mock_result = FormList(forms=mock_forms, count=5, total=20)
        mock_client.get_forms.return_value = mock_result
        
        # Create params with pagination
        params = GetFormsParams(
            location_id="loc123",
            limit=5,
            skip=10,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_forms"](params)
        
        # Verify
        assert result["success"] is True
        assert len(result["forms"]) == 5
        assert result["total"] == 20
        mock_client.get_forms.assert_called_once_with(
            location_id="loc123",
            limit=5,
            skip=10
        )

    @pytest.mark.asyncio
    async def test_get_all_form_submissions(self, setup_tools):
        """Test get_all_form_submissions tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_submissions = [
            FormSubmission(
                id="sub1",
                formId="form123",
                locationId="loc123",
                contactId="contact1",
                data={"firstName": "John", "lastName": "Doe", "email": "john@example.com"},
                submittedAt=datetime(2025, 6, 8, 10, 0, tzinfo=timezone.utc)
            ),
            FormSubmission(
                id="sub2",
                formId="form123",
                locationId="loc123",
                contactId="contact2",
                data={"firstName": "Jane", "lastName": "Smith", "email": "jane@example.com"},
                submittedAt=datetime(2025, 6, 8, 11, 0, tzinfo=timezone.utc)
            )
        ]
        mock_result = FormSubmissionList(submissions=mock_submissions, count=2, total=10)
        mock_client.get_all_submissions.return_value = mock_result
        
        # Create params
        params = GetAllSubmissionsParams(
            location_id="loc123",
            limit=10,
            skip=0,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_all_form_submissions"](params)
        
        # Verify
        assert result["success"] is True
        assert len(result["submissions"]) == 2
        assert result["count"] == 2
        assert result["total"] == 10
        assert result["submissions"][0]["id"] == "sub1"
        assert result["submissions"][1]["id"] == "sub2"
        mock_client.get_all_submissions.assert_called_once_with(
            location_id="loc123",
            form_id=None,
            contact_id=None,
            start_date=None,
            end_date=None,
            limit=10,
            skip=0
        )

    @pytest.mark.asyncio
    async def test_get_all_form_submissions_with_filters(self, setup_tools):
        """Test get_all_form_submissions with filters."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_result = FormSubmissionList(submissions=[], count=0, total=0)
        mock_client.get_all_submissions.return_value = mock_result
        
        # Create params with filters
        params = GetAllSubmissionsParams(
            location_id="loc123",
            form_id="form123",
            contact_id="contact123",
            start_date="2025-06-01",
            end_date="2025-06-30",
            limit=20,
            skip=5,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_all_form_submissions"](params)
        
        # Verify filters were passed
        assert result["success"] is True
        mock_client.get_all_submissions.assert_called_once_with(
            location_id="loc123",
            form_id="form123",
            contact_id="contact123",
            start_date="2025-06-01",
            end_date="2025-06-30",
            limit=20,
            skip=5
        )

    @pytest.mark.asyncio
    async def test_upload_form_file(self, setup_tools):
        """Test upload_form_file tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_result = {"uploadUrl": "https://example.com/uploaded/file.pdf"}
        mock_client.upload_form_file.return_value = mock_result
        
        # Create params
        params = UploadFormFileParams(
            contact_id="contact123",
            location_id="loc123",
            field_id="field123",
            file_name="document.pdf",
            file_content="base64encodedcontent",
            content_type="application/pdf",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["upload_form_file"](params)
        
        # Verify
        assert result["success"] is True
        assert result["result"]["uploadUrl"] == "https://example.com/uploaded/file.pdf"
        
        # Verify the client was called with correct data
        upload_call_args = mock_client.upload_form_file.call_args[0][0]
        assert isinstance(upload_call_args, FormFileUploadRequest)
        assert upload_call_args.contactId == "contact123"
        assert upload_call_args.locationId == "loc123"
        assert upload_call_args.fieldId == "field123"
        assert upload_call_args.fileName == "document.pdf"
        assert upload_call_args.fileContent == "base64encodedcontent"
        assert upload_call_args.contentType == "application/pdf"

    @pytest.mark.asyncio
    async def test_upload_form_file_default_content_type(self, setup_tools):
        """Test upload_form_file with default content type."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_result = {"uploadUrl": "https://example.com/uploaded/file.jpg"}
        mock_client.upload_form_file.return_value = mock_result
        
        # Create params without content_type
        params = UploadFormFileParams(
            contact_id="contact123",
            location_id="loc123",
            field_id="field123",
            file_name="image.jpg",
            file_content="base64encodedimage",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["upload_form_file"](params)
        
        # Verify
        assert result["success"] is True
        
        # Verify default content type
        upload_call_args = mock_client.upload_form_file.call_args[0][0]
        assert upload_call_args.contentType == "application/octet-stream"