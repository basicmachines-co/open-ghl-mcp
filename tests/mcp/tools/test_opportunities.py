"""Tests for the mcp.tools.opportunities module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.models.opportunity import (
    Opportunity,
    OpportunitySearchResult,
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityStatus,
    OpportunitySearchFilters,
    Pipeline,
    PipelineStage,
)
from src.mcp.params.opportunities import (
    GetOpportunitiesParams,
    GetOpportunityParams,
    CreateOpportunityParams,
    UpdateOpportunityParams,
    DeleteOpportunityParams,
    UpdateOpportunityStatusParams,
    GetPipelinesParams,
)
from src.mcp.tools.opportunities import _register_opportunity_tools


class TestOpportunityTools:
    """Test cases for opportunity tools."""

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
    def mock_oauth_service(self):
        """Create a mock OAuth service."""
        mock = Mock()
        mock.settings = Mock()
        mock.settings.auth_mode = "custom"
        mock.settings.ghl_client_id = "test_client_id"
        mock.settings.ghl_client_secret = "test_secret"
        mock.settings.supabase_url = "https://test.supabase.co"
        mock.settings.supabase_access_key = "test_key"
        mock._standard_auth = None
        return mock

    @pytest.fixture
    def setup_tools(self, mock_mcp, mock_get_client, mock_oauth_service):
        """Set up opportunity tools with mocks."""
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
        
        # Register the tools with oauth service
        _register_opportunity_tools(mock_mcp, get_client_func, mock_oauth_service)
        
        return tools, mock_client

    @pytest.mark.asyncio
    async def test_get_opportunities(self, setup_tools):
        """Test get_opportunities tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_opportunities = [
            Opportunity(
                id="opp1",
                pipelineId="pipe123",
                locationId="loc123",
                name="Deal 1",
                pipelineStageId="stage1",
                status=OpportunityStatus.OPEN,
                contactId="contact1",
                monetaryValue=5000.0,
                assignedTo="user1",
                source="Website",
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc),
            ),
            Opportunity(
                id="opp2",
                pipelineId="pipe123",
                locationId="loc123",
                name="Deal 2",
                pipelineStageId="stage2",
                status=OpportunityStatus.WON,
                contactId="contact2",
                monetaryValue=10000.0,
                assignedTo="user2",
                source="Referral",
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc),
            )
        ]
        from src.models.opportunity import Meta
        mock_result = OpportunitySearchResult(
            opportunities=mock_opportunities,
            meta=Meta(total=10, currentPage=1, nextPage=None, prevPage=None)
        )
        mock_client.get_opportunities.return_value = mock_result
        
        # Create params
        params = GetOpportunitiesParams(
            location_id="loc123",
            limit=10,
            skip=0,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_opportunities"](params)
        
        # Verify
        assert result["success"] is True
        assert len(result["opportunities"]) == 2
        assert result["count"] == 2
        assert result["total"] == 10
        assert result["opportunities"][0]["id"] == "opp1"
        assert result["opportunities"][0]["name"] == "Deal 1"
        assert result["opportunities"][1]["id"] == "opp2"
        mock_client.get_opportunities.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_opportunities_with_filters(self, setup_tools):
        """Test get_opportunities with filters."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_result = OpportunitySearchResult(opportunities=[])
        mock_client.get_opportunities.return_value = mock_result
        
        # Create params with filters
        params = GetOpportunitiesParams(
            location_id="loc123",
            pipeline_id="pipe123",
            pipeline_stage_id="stage123",
            assigned_to="user123",
            status="open",
            contact_id="contact123",
            query="urgent",
            limit=20,
            skip=10,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_opportunities"](params)
        
        # Verify
        assert result["success"] is True
        
        # Check the filters were passed correctly
        call_args = mock_client.get_opportunities.call_args
        assert call_args[1]["location_id"] == "loc123"
        assert call_args[1]["limit"] == 20
        assert call_args[1]["skip"] == 10
        
        filters = call_args[1]["filters"]
        assert filters.pipelineId == "pipe123"
        assert filters.pipelineStageId == "stage123"
        assert filters.assignedTo == "user123"
        assert filters.status == "open"
        assert filters.contactId == "contact123"
        assert filters.query == "urgent"

    @pytest.mark.asyncio
    async def test_get_opportunity(self, setup_tools):
        """Test get_opportunity tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_opportunity = Opportunity(
            id="opp123",
            pipelineId="pipe123",
            locationId="loc123",
            name="Test Deal",
            pipelineStageId="stage123",
            status=OpportunityStatus.OPEN,
            contactId="contact123",
            monetaryValue=7500.0,
            assignedTo="user123",
            source="API",
            notes="Test opportunity",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
        )
        mock_client.get_opportunity.return_value = mock_opportunity
        
        # Create params
        params = GetOpportunityParams(
            opportunity_id="opp123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_opportunity"](params)
        
        # Verify
        assert result["success"] is True
        assert result["opportunity"]["id"] == "opp123"
        assert result["opportunity"]["name"] == "Test Deal"
        assert result["opportunity"]["monetaryValue"] == 7500.0
        mock_client.get_opportunity.assert_called_once_with("opp123", "loc123")

    @pytest.mark.asyncio
    async def test_create_opportunity(self, setup_tools):
        """Test create_opportunity tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_opportunity = Opportunity(
            id="opp123",
            pipelineId="pipe123",
            locationId="loc123",
            name="New Deal",
            pipelineStageId="stage123",
            status=OpportunityStatus.OPEN,
            contactId="contact123",
            monetaryValue=5000.0,
            assignedTo="user123",
            source="Website",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
        )
        mock_client.create_opportunity.return_value = mock_opportunity
        
        # Create params
        params = CreateOpportunityParams(
            pipeline_id="pipe123",
            location_id="loc123",
            name="New Deal",
            pipeline_stage_id="stage123",
            contact_id="contact123",
            monetary_value=5000.0,
            assigned_to="user123",
            source="Website",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["create_opportunity"](params)
        
        # Verify
        assert result["success"] is True
        assert result["opportunity"]["id"] == "opp123"
        assert result["opportunity"]["name"] == "New Deal"
        
        # Verify the client was called with correct data
        create_call_args = mock_client.create_opportunity.call_args[0][0]
        assert create_call_args.pipelineId == "pipe123"
        assert create_call_args.locationId == "loc123"
        assert create_call_args.name == "New Deal"
        assert create_call_args.pipelineStageId == "stage123"
        assert create_call_args.contactId == "contact123"
        assert create_call_args.monetaryValue == 5000.0
        assert create_call_args.status == OpportunityStatus.OPEN  # Default

    @pytest.mark.asyncio
    async def test_create_opportunity_with_custom_fields(self, setup_tools):
        """Test create_opportunity with custom fields."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_opportunity = Opportunity(
            id="opp123",
            pipelineId="pipe123",
            locationId="loc123",
            name="New Deal",
            pipelineStageId="stage123",
            status=OpportunityStatus.OPEN,
            contactId="contact123",
            customFields=[{"key": "priority", "value": "high"}],
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
        )
        mock_client.create_opportunity.return_value = mock_opportunity
        
        # Create params with custom fields
        params = CreateOpportunityParams(
            pipeline_id="pipe123",
            location_id="loc123",
            name="New Deal",
            pipeline_stage_id="stage123",
            contact_id="contact123",
            custom_fields={"priority": "high"},
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["create_opportunity"](params)
        
        # Verify
        assert result["success"] is True
        
        # Verify custom fields were passed
        create_call_args = mock_client.create_opportunity.call_args[0][0]
        assert create_call_args.customFields == [{"key": "priority", "value": "high"}]

    @pytest.mark.asyncio
    async def test_update_opportunity(self, setup_tools):
        """Test update_opportunity tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_opportunity = Opportunity(
            id="opp123",
            pipelineId="pipe123",
            locationId="loc123",
            name="Updated Deal",
            pipelineStageId="stage456",
            status=OpportunityStatus.WON,
            contactId="contact123",
            monetaryValue=8000.0,
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
        )
        mock_client.update_opportunity.return_value = mock_opportunity
        
        # Create params
        params = UpdateOpportunityParams(
            opportunity_id="opp123",
            location_id="loc123",
            name="Updated Deal",
            pipeline_stage_id="stage456",
            status="won",
            monetary_value=8000.0,
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["update_opportunity"](params)
        
        # Verify
        assert result["success"] is True
        assert result["opportunity"]["name"] == "Updated Deal"
        assert result["opportunity"]["status"] == OpportunityStatus.WON
        
        # Verify client call
        update_data = mock_client.update_opportunity.call_args[0][1]
        assert update_data.name == "Updated Deal"
        assert update_data.pipelineStageId == "stage456"
        assert update_data.status == "won"
        assert update_data.monetaryValue == 8000.0

    @pytest.mark.asyncio
    async def test_delete_opportunity_success(self, setup_tools):
        """Test delete_opportunity tool with success."""
        tools, mock_client = setup_tools
        
        # Mock successful deletion
        mock_client.delete_opportunity.return_value = True
        
        # Create params
        params = DeleteOpportunityParams(
            opportunity_id="opp123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["delete_opportunity"](params)
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Opportunity deleted successfully"
        mock_client.delete_opportunity.assert_called_once_with("opp123", "loc123")

    @pytest.mark.asyncio
    async def test_delete_opportunity_failure(self, setup_tools):
        """Test delete_opportunity tool with failure."""
        tools, mock_client = setup_tools
        
        # Mock failed deletion
        mock_client.delete_opportunity.return_value = False
        
        # Create params
        params = DeleteOpportunityParams(
            opportunity_id="opp123",
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["delete_opportunity"](params)
        
        # Verify
        assert result["success"] is False
        assert result["message"] == "Failed to delete opportunity"

    @pytest.mark.asyncio
    async def test_update_opportunity_status(self, setup_tools):
        """Test update_opportunity_status tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_opportunity = Opportunity(
            id="opp123",
            pipelineId="pipe123",
            locationId="loc123",
            name="Deal",
            pipelineStageId="stage123",
            status=OpportunityStatus.LOST,
            contactId="contact123",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
        )
        mock_client.update_opportunity_status.return_value = mock_opportunity
        
        # Create params
        params = UpdateOpportunityStatusParams(
            opportunity_id="opp123",
            location_id="loc123",
            status="lost",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["update_opportunity_status"](params)
        
        # Verify
        assert result["success"] is True
        assert result["opportunity"]["status"] == OpportunityStatus.LOST
        mock_client.update_opportunity_status.assert_called_once_with(
            opportunity_id="opp123",
            status="lost",
            location_id="loc123"
        )

    @pytest.mark.asyncio
    async def test_get_pipelines(self, setup_tools):
        """Test get_pipelines tool."""
        tools, mock_client = setup_tools
        
        # Mock the client response
        mock_pipelines = [
            Pipeline(
                id="pipe1",
                name="Sales Pipeline",
                locationId="loc123",
                stages=[
                    PipelineStage(
                        id="stage1",
                        name="Lead",
                        position=1
                    ),
                    PipelineStage(
                        id="stage2",
                        name="Qualified",
                        position=2
                    ),
                    PipelineStage(
                        id="stage3",
                        name="Proposal",
                        position=3
                    )
                ]
            ),
            Pipeline(
                id="pipe2",
                name="Support Pipeline",
                locationId="loc123",
                stages=[
                    PipelineStage(
                        id="stage4",
                        name="New Ticket",
                        position=1
                    ),
                    PipelineStage(
                        id="stage5",
                        name="In Progress",
                        position=2
                    )
                ]
            )
        ]
        mock_client.get_pipelines.return_value = mock_pipelines
        
        # Create params
        params = GetPipelinesParams(
            location_id="loc123",
            access_token="test_token"
        )
        
        # Call the tool
        result = await tools["get_pipelines"](params)
        
        # Verify
        assert result["success"] is True
        assert len(result["pipelines"]) == 2
        assert result["count"] == 2
        assert result["pipelines"][0]["id"] == "pipe1"
        assert result["pipelines"][0]["name"] == "Sales Pipeline"
        assert len(result["pipelines"][0]["stages"]) == 3
        assert result["pipelines"][1]["id"] == "pipe2"
        mock_client.get_pipelines.assert_called_once_with("loc123")

    @pytest.mark.asyncio
    async def test_debug_config(self, setup_tools):
        """Test debug_config tool."""
        tools, mock_client = setup_tools
        
        # Mock file system checks
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("pathlib.Path.cwd") as mock_cwd, \
             patch("builtins.open", create=True) as mock_open, \
             patch("os.environ.get") as mock_env_get:
            
            # Setup mocks
            mock_exists.return_value = True
            mock_cwd.return_value = "/test/path"
            mock_env_get.side_effect = lambda key, default=None: {
                "AUTH_MODE": "custom",
                "GHL_CLIENT_ID": "test_client_id_12345"
            }.get(key, default)
            
            # Mock token file content
            mock_open.return_value.__enter__.return_value.read.return_value = '''
            {
                "expires_at": "2025-12-31T23:59:59Z"
            }
            '''
            
            # Call the tool
            result = await tools["debug_config"]()
            
            # Verify basic structure
            assert "environment" in result
            assert "files" in result
            assert "oauth_service" in result
            assert "token_status" in result
            
            # Verify oauth service info
            assert result["oauth_service"]["auth_mode"] == "custom"
            assert result["oauth_service"]["ghl_client_id"] == "test_clien..."