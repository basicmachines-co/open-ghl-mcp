"""Tests for the api.opportunities module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.api.opportunities import OpportunitiesClient
from src.models.opportunity import (
    Opportunity,
    OpportunityCreate,
    OpportunityUpdate,
    OpportunitySearchResult,
    OpportunitySearchFilters,
    Pipeline,
    PipelineStage,
)


class TestOpportunitiesClient:
    """Test cases for the OpportunitiesClient class."""

    @pytest.fixture
    def mock_oauth_service(self):
        """Create a mock OAuth service."""
        service = Mock()
        service.get_valid_token = AsyncMock(return_value="test_token")
        service.get_location_token = AsyncMock(return_value="location_token")
        return service

    @pytest.fixture
    def opportunities_client(self, mock_oauth_service):
        """Create an OpportunitiesClient instance."""
        return OpportunitiesClient(mock_oauth_service)

    @pytest.fixture
    def sample_opportunity_data(self):
        """Sample opportunity data for testing."""
        return {
            "id": "opp123",
            "locationId": "loc123",
            "contactId": "contact123",
            "pipelineId": "pipeline123",
            "pipelineStageId": "stage123",
            "name": "Test Opportunity",
            "status": "open",
            "monetaryValue": 5000.0,
            "assignedTo": "user123",
            "source": "website",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.fixture
    def sample_pipeline_data(self):
        """Sample pipeline data for testing."""
        return {
            "id": "pipeline123",
            "name": "Sales Pipeline",
            "locationId": "loc123",
            "stages": [
                {
                    "id": "stage1",
                    "name": "Lead",
                    "position": 0,
                },
                {
                    "id": "stage2",
                    "name": "Qualified",
                    "position": 1,
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_opportunities_basic(self, opportunities_client):
        """Test getting opportunities with basic parameters."""
        mock_opportunities = [
            {
                "id": "opp1",
                "name": "Opportunity 1",
                "locationId": "loc123",
                "status": "open",
                "pipelineId": "pipeline123",
                "pipelineStageId": "stage1",
                "contactId": "contact1",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "opp2",
                "name": "Opportunity 2",
                "locationId": "loc123",
                "status": "won",
                "pipelineId": "pipeline123",
                "pipelineStageId": "stage2",
                "contactId": "contact2",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
        ]
        mock_response = Mock()
        mock_response.json.return_value = {
            "opportunities": mock_opportunities,
            "meta": {"total": 2, "currentPage": 1},
            "aggregations": {"pipelines": {"pipeline123": {"open": 1, "won": 1}}},
        }

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await opportunities_client.get_opportunities("loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "GET",
                "/opportunities/search",
                params={"location_id": "loc123", "limit": 100},
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, OpportunitySearchResult)
            assert len(result.opportunities) == 2
            assert result.meta.total == 2
            assert result.meta.currentPage == 1
            assert result.aggregations.pipelines == {"pipeline123": {"open": 1, "won": 1}}

    @pytest.mark.asyncio
    async def test_get_opportunities_with_filters(self, opportunities_client):
        """Test getting opportunities with various filters."""
        start_date = datetime.now(timezone.utc)
        end_date = datetime.now(timezone.utc)
        filters = OpportunitySearchFilters(
            pipelineId="pipeline123",
            pipelineStageId="stage123",
            status="open",
            assignedTo="user123",
            startDate=start_date,
            endDate=end_date,
            query="test search",
        )

        mock_response = Mock()
        mock_response.json.return_value = {"opportunities": [], "meta": {"total": 0, "currentPage": 1}}

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await opportunities_client.get_opportunities(
                location_id="loc123",
                limit=50,
                skip=10,
                filters=filters
            )

            # Verify request parameters
            mock_request.assert_called_once_with(
                "GET",
                "/opportunities/search",
                params={
                    "location_id": "loc123",
                    "limit": 50,
                    "skip": 10,
                    "pipelineId": "pipeline123",
                    "pipelineStageId": "stage123",
                    "status": "open",
                    "assignedTo": "user123",
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "query": "test search",
                },
                location_id="loc123"
            )

    @pytest.mark.asyncio
    async def test_get_opportunities_skip_zero_not_included(self, opportunities_client):
        """Test that skip=0 is not included in params."""
        mock_response = Mock()
        mock_response.json.return_value = {"opportunities": []}

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            await opportunities_client.get_opportunities("loc123", skip=0)

            # Verify skip is not in params when 0
            call_params = mock_request.call_args[1]["params"]
            assert "skip" not in call_params

    @pytest.mark.asyncio
    async def test_get_opportunity(self, opportunities_client, sample_opportunity_data):
        """Test getting a specific opportunity."""
        mock_response = Mock()
        mock_response.json.return_value = {"opportunity": sample_opportunity_data}

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await opportunities_client.get_opportunity("opp123", "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "GET",
                "/opportunities/opp123",
                params={"locationId": "loc123"},
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Opportunity)
            assert result.id == "opp123"
            assert result.name == "Test Opportunity"
            assert result.monetaryValue == 5000.0

    @pytest.mark.asyncio
    async def test_get_opportunity_without_wrapper(self, opportunities_client, sample_opportunity_data):
        """Test getting an opportunity when API returns data without 'opportunity' wrapper."""
        mock_response = Mock()
        mock_response.json.return_value = sample_opportunity_data  # No wrapper

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await opportunities_client.get_opportunity("opp123", "loc123")

            # Should still parse correctly
            assert isinstance(result, Opportunity)
            assert result.id == "opp123"

    @pytest.mark.asyncio
    async def test_create_opportunity(self, opportunities_client, sample_opportunity_data):
        """Test creating a new opportunity."""
        opportunity_create = OpportunityCreate(
            locationId="loc123",
            contactId="contact123",
            pipelineId="pipeline123",
            pipelineStageId="stage123",
            name="New Opportunity",
            monetaryValue=10000.0,
            status="open",
            assignedTo="user123",
        )

        mock_response = Mock()
        mock_response.json.return_value = {"opportunity": sample_opportunity_data}

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await opportunities_client.create_opportunity(opportunity_create)

            # Verify request - note the trailing slash
            mock_request.assert_called_once_with(
                "POST",
                "/opportunities/",
                json={
                    "locationId": "loc123",
                    "contactId": "contact123",
                    "pipelineId": "pipeline123",
                    "pipelineStageId": "stage123",
                    "name": "New Opportunity",
                    "monetaryValue": 10000.0,
                    "status": "open",
                    "assignedTo": "user123",
                },
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Opportunity)
            assert result.id == "opp123"

    @pytest.mark.asyncio
    async def test_update_opportunity(self, opportunities_client, sample_opportunity_data):
        """Test updating an existing opportunity."""
        opportunity_update = OpportunityUpdate(
            name="Updated Opportunity",
            monetaryValue=15000.0,
            status="won",
            pipelineStageId="stage2",
        )

        mock_response = Mock()
        mock_response.json.return_value = {"opportunity": {**sample_opportunity_data, "name": "Updated Opportunity"}}

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await opportunities_client.update_opportunity("opp123", opportunity_update, "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "PUT",
                "/opportunities/opp123",
                json={
                    "name": "Updated Opportunity",
                    "monetaryValue": 15000.0,
                    "status": "won",
                    "pipelineStageId": "stage2",
                },
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Opportunity)
            assert result.name == "Updated Opportunity"

    @pytest.mark.asyncio
    async def test_delete_opportunity_success(self, opportunities_client):
        """Test successfully deleting an opportunity."""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await opportunities_client.delete_opportunity("opp123", "loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "DELETE",
                "/opportunities/opp123",
                params={"locationId": "loc123"},
                location_id="loc123"
            )

            # Verify result
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_opportunity_failure(self, opportunities_client):
        """Test failed opportunity deletion."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await opportunities_client.delete_opportunity("opp123", "loc123")

            # Should return False for non-200 status
            assert result is False

    @pytest.mark.asyncio
    async def test_update_opportunity_status(self, opportunities_client, sample_opportunity_data):
        """Test updating opportunity status."""
        # Mock the status update request
        mock_status_response = Mock()
        mock_status_response.json.return_value = {"success": True}

        # Mock the get_opportunity call that follows
        mock_get_response = Mock()
        mock_get_response.json.return_value = {"opportunity": {**sample_opportunity_data, "status": "won"}}

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [mock_status_response, mock_get_response]

            result = await opportunities_client.update_opportunity_status("opp123", "won", "loc123")

            # Verify both requests were made
            assert mock_request.call_count == 2

            # Verify status update request
            mock_request.assert_any_call(
                "PUT",
                "/opportunities/opp123/status",
                json={"status": "won"},
                location_id="loc123"
            )

            # Verify get_opportunity request
            mock_request.assert_any_call(
                "GET",
                "/opportunities/opp123",
                params={"locationId": "loc123"},
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, Opportunity)
            assert result.status == "won"

    @pytest.mark.asyncio
    async def test_get_pipelines(self, opportunities_client, sample_pipeline_data):
        """Test getting pipelines for a location."""
        mock_pipelines = [sample_pipeline_data, {**sample_pipeline_data, "id": "pipeline124", "name": "Support Pipeline"}]
        mock_response = Mock()
        mock_response.json.return_value = {"pipelines": mock_pipelines}

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            result = await opportunities_client.get_pipelines("loc123")

            # Verify request
            mock_request.assert_called_once_with(
                "GET",
                "/opportunities/pipelines",
                params={"locationId": "loc123"},
                location_id="loc123"
            )

            # Verify result
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(p, Pipeline) for p in result)
            assert result[0].id == "pipeline123"
            assert result[0].name == "Sales Pipeline"
            assert len(result[0].stages) == 2

    @pytest.mark.asyncio
    async def test_get_pipelines_empty_response(self, opportunities_client):
        """Test handling empty pipelines response."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # Empty response

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await opportunities_client.get_pipelines("loc123")

            # Should handle gracefully
            assert isinstance(result, list)
            assert result == []

    @pytest.mark.asyncio
    async def test_opportunity_search_result_without_meta(self, opportunities_client):
        """Test OpportunitySearchResult handles missing meta and aggregations."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "opportunities": [{
                "id": "opp1",
                "name": "Test",
                "locationId": "loc123",
                "status": "open",
                "pipelineId": "pipeline123",
                "pipelineStageId": "stage1",
                "contactId": "contact123",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }]
        }

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await opportunities_client.get_opportunities("loc123")

            assert len(result.opportunities) == 1
            assert result.meta is None
            assert result.aggregations is None

    @pytest.mark.asyncio
    async def test_filters_exclude_none_values(self, opportunities_client):
        """Test that filters with None values are excluded from params."""
        filters = OpportunitySearchFilters(
            pipelineId="pipeline123",
            status=None,  # Should be excluded
            assignedTo=None,  # Should be excluded
        )

        mock_response = Mock()
        mock_response.json.return_value = {"opportunities": []}

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
            await opportunities_client.get_opportunities("loc123", filters=filters)

            # Verify only non-None values are included
            call_params = mock_request.call_args[1]["params"]
            assert "pipelineId" in call_params
            assert "status" not in call_params
            assert "assignedTo" not in call_params

    @pytest.mark.asyncio
    async def test_create_opportunity_without_wrapper(self, opportunities_client, sample_opportunity_data):
        """Test creating opportunity when API returns data without wrapper."""
        opportunity_create = OpportunityCreate(
            locationId="loc123",
            contactId="contact123",
            pipelineId="pipeline123",
            pipelineStageId="stage123",
            name="New Opportunity",
        )

        mock_response = Mock()
        mock_response.json.return_value = sample_opportunity_data  # No wrapper

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await opportunities_client.create_opportunity(opportunity_create)

            # Should still parse correctly
            assert isinstance(result, Opportunity)
            assert result.id == "opp123"

    @pytest.mark.asyncio
    async def test_update_opportunity_without_wrapper(self, opportunities_client, sample_opportunity_data):
        """Test updating opportunity when API returns data without wrapper."""
        opportunity_update = OpportunityUpdate(name="Updated")

        mock_response = Mock()
        mock_response.json.return_value = sample_opportunity_data  # No wrapper

        with patch.object(opportunities_client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await opportunities_client.update_opportunity("opp123", opportunity_update, "loc123")

            # Should still parse correctly
            assert isinstance(result, Opportunity)
            assert result.id == "opp123"