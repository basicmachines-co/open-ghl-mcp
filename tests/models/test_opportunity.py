"""Tests for the models.opportunity module."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models.opportunity import (
    OpportunityStatus,
    OpportunityCreate,
    OpportunityUpdate,
    Pipeline,
    PipelineStage,
    Attribution,
    Relation,
    Contact,
    Opportunity,
    Meta,
    Aggregations,
    OpportunitySearchResult,
    OpportunitySearchFilters,
)


class TestOpportunityStatus:
    """Test cases for OpportunityStatus enum."""

    def test_opportunity_status_values(self):
        """Test all opportunity status values."""
        assert OpportunityStatus.OPEN.value == "open"
        assert OpportunityStatus.WON.value == "won"
        assert OpportunityStatus.LOST.value == "lost"
        assert OpportunityStatus.ABANDONED.value == "abandoned"


class TestOpportunityCreate:
    """Test cases for OpportunityCreate model."""

    def test_opportunity_create_minimal(self):
        """Test creating OpportunityCreate with minimal required fields."""
        opp = OpportunityCreate(
            pipelineId="pipe123",
            locationId="loc123",
            name="New Deal",
            pipelineStageId="stage123",
            contactId="contact123"
        )
        
        assert opp.pipelineId == "pipe123"
        assert opp.locationId == "loc123"
        assert opp.name == "New Deal"
        assert opp.pipelineStageId == "stage123"
        assert opp.contactId == "contact123"
        assert opp.status == OpportunityStatus.OPEN  # Default
        assert opp.monetaryValue is None
        assert opp.assignedTo is None

    def test_opportunity_create_full(self):
        """Test creating OpportunityCreate with all fields."""
        custom_fields = [{"id": "field1", "value": "custom"}]
        
        opp = OpportunityCreate(
            pipelineId="pipe123",
            locationId="loc123",
            name="Enterprise Deal",
            pipelineStageId="stage456",
            contactId="contact123",
            status=OpportunityStatus.OPEN,
            monetaryValue=50000.00,
            assignedTo="user123",
            source="Website",
            customFields=custom_fields
        )
        
        assert opp.name == "Enterprise Deal"
        assert opp.monetaryValue == 50000.00
        assert opp.assignedTo == "user123"
        assert opp.source == "Website"
        assert opp.customFields == custom_fields

    def test_opportunity_create_status_options(self):
        """Test different status options on creation."""
        # Default status
        opp1 = OpportunityCreate(
            pipelineId="pipe123",
            locationId="loc123",
            name="Deal 1",
            pipelineStageId="stage123",
            contactId="contact123"
        )
        assert opp1.status == OpportunityStatus.OPEN
        
        # Custom status
        opp2 = OpportunityCreate(
            pipelineId="pipe123",
            locationId="loc123",
            name="Deal 2",
            pipelineStageId="stage123",
            contactId="contact123",
            status=OpportunityStatus.WON
        )
        assert opp2.status == OpportunityStatus.WON

    def test_opportunity_create_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunityCreate(
                pipelineId="pipe123",
                locationId="loc123"
                # Missing name, pipelineStageId, contactId
            )
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "name" in error_fields
        assert "pipelineStageId" in error_fields
        assert "contactId" in error_fields


class TestOpportunityUpdate:
    """Test cases for OpportunityUpdate model."""

    def test_opportunity_update_all_optional(self):
        """Test that all OpportunityUpdate fields are optional."""
        update = OpportunityUpdate()
        
        assert update.name is None
        assert update.pipelineStageId is None
        assert update.status is None
        assert update.monetaryValue is None
        assert update.assignedTo is None
        assert update.source is None
        assert update.customFields is None

    def test_opportunity_update_partial(self):
        """Test updating only some fields."""
        update = OpportunityUpdate(
            name="Updated Deal Name",
            monetaryValue=75000.00,
            status=OpportunityStatus.WON
        )
        
        assert update.name == "Updated Deal Name"
        assert update.monetaryValue == 75000.00
        assert update.status == OpportunityStatus.WON
        assert update.pipelineStageId is None  # Not updated

    def test_opportunity_update_stage_change(self):
        """Test updating pipeline stage."""
        update = OpportunityUpdate(
            pipelineStageId="stage789",
            assignedTo="user456"
        )
        
        assert update.pipelineStageId == "stage789"
        assert update.assignedTo == "user456"

    def test_opportunity_update_custom_fields(self):
        """Test updating custom fields."""
        custom_fields = [
            {"id": "field1", "value": "updated value"},
            {"id": "field2", "value": 123}
        ]
        
        update = OpportunityUpdate(customFields=custom_fields)
        
        assert update.customFields == custom_fields
        assert len(update.customFields) == 2


class TestPipeline:
    """Test cases for Pipeline model."""

    def test_pipeline_minimal(self):
        """Test creating Pipeline with minimal required fields."""
        pipeline = Pipeline(
            id="pipe123",
            name="Sales Pipeline"
        )
        
        assert pipeline.id == "pipe123"
        assert pipeline.name == "Sales Pipeline"
        assert pipeline.stages is None
        assert pipeline.dateAdded is None
        assert pipeline.dateUpdated is None

    def test_pipeline_with_stages(self):
        """Test Pipeline with stages."""
        stages = [
            PipelineStage(id="stage1", name="Lead", position=1),
            PipelineStage(id="stage2", name="Qualified", position=2),
            PipelineStage(id="stage3", name="Proposal", position=3)
        ]
        
        pipeline = Pipeline(
            id="pipe123",
            name="Sales Pipeline",
            stages=stages
        )
        
        assert len(pipeline.stages) == 3
        assert pipeline.stages[0].name == "Lead"
        assert pipeline.stages[1].position == 2
        assert pipeline.stages[2].id == "stage3"

    def test_pipeline_datetime_parsing(self):
        """Test Pipeline datetime field parsing."""
        # With Z suffix
        pipeline1 = Pipeline(
            id="pipe123",
            name="Pipeline 1",
            dateAdded="2025-06-08T03:01:58.848Z",
            dateUpdated="2025-06-09T10:30:00.000Z"
        )
        
        assert isinstance(pipeline1.dateAdded, datetime)
        assert isinstance(pipeline1.dateUpdated, datetime)
        assert pipeline1.dateAdded.tzinfo is not None
        
        # With standard ISO format
        pipeline2 = Pipeline(
            id="pipe456",
            name="Pipeline 2",
            dateAdded="2025-06-08T03:01:58+00:00"
        )
        
        assert isinstance(pipeline2.dateAdded, datetime)

    def test_pipeline_invalid_datetime(self):
        """Test Pipeline with invalid datetime returns None."""
        pipeline = Pipeline(
            id="pipe123",
            name="Pipeline",
            dateAdded="invalid-date"
        )
        
        assert pipeline.dateAdded is None

    def test_pipeline_with_origin_id(self):
        """Test Pipeline with originId."""
        pipeline = Pipeline(
            id="pipe123",
            name="Imported Pipeline",
            originId="external123"
        )
        
        assert pipeline.originId == "external123"


class TestPipelineStage:
    """Test cases for PipelineStage model."""

    def test_pipeline_stage_minimal(self):
        """Test creating PipelineStage with required fields."""
        stage = PipelineStage(
            id="stage123",
            name="Qualification",
            position=2
        )
        
        assert stage.id == "stage123"
        assert stage.name == "Qualification"
        assert stage.position == 2
        assert stage.originId is None
        assert stage.showInFunnel is None

    def test_pipeline_stage_full(self):
        """Test PipelineStage with all fields."""
        stage = PipelineStage(
            id="stage123",
            name="Negotiation",
            position=4,
            originId="ext456",
            showInFunnel=True,
            showInPieChart=True
        )
        
        assert stage.originId == "ext456"
        assert stage.showInFunnel is True
        assert stage.showInPieChart is True

    def test_pipeline_stage_position_validation(self):
        """Test that position is required and must be integer."""
        # Valid stage
        stage = PipelineStage(id="s1", name="Stage 1", position=1)
        assert stage.position == 1
        
        # Missing position
        with pytest.raises(ValidationError) as exc_info:
            PipelineStage(id="s2", name="Stage 2")
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "position" for e in errors)


class TestAttribution:
    """Test cases for Attribution model."""

    def test_attribution_all_optional(self):
        """Test that all Attribution fields are optional."""
        attr = Attribution()
        
        assert attr.utmSessionSource is None
        assert attr.medium is None
        assert attr.mediumId is None
        assert attr.url is None
        assert attr.isFirst is None
        assert attr.isLast is None

    def test_attribution_full(self):
        """Test Attribution with all fields."""
        attr = Attribution(
            utmSessionSource="google",
            medium="cpc",
            mediumId="campaign123",
            url="https://example.com/landing",
            isFirst=True,
            isLast=False
        )
        
        assert attr.utmSessionSource == "google"
        assert attr.medium == "cpc"
        assert attr.mediumId == "campaign123"
        assert attr.url == "https://example.com/landing"
        assert attr.isFirst is True
        assert attr.isLast is False


class TestRelation:
    """Test cases for Relation model."""

    def test_relation_minimal(self):
        """Test creating Relation with required fields."""
        relation = Relation(
            associationId="assoc123",
            relationId="rel123",
            primary=True,
            objectKey="contact",
            recordId="rec123",
            fullName="John Doe",
            contactName="John",
            email="john@example.com"
        )
        
        assert relation.associationId == "assoc123"
        assert relation.primary is True
        assert relation.objectKey == "contact"
        assert relation.email == "john@example.com"
        assert relation.tags == []  # Default empty
        assert relation.companyName is None

    def test_relation_full(self):
        """Test Relation with all fields."""
        relation = Relation(
            associationId="assoc123",
            relationId="rel123",
            primary=False,
            objectKey="contact",
            recordId="rec123",
            fullName="Jane Smith",
            contactName="Jane",
            companyName="Acme Corp",
            email="jane@acme.com",
            phone="+1234567890",
            tags=["vip", "enterprise"],
            attributed=True
        )
        
        assert relation.companyName == "Acme Corp"
        assert relation.phone == "+1234567890"
        assert relation.tags == ["vip", "enterprise"]
        assert relation.attributed is True

    def test_relation_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Relation(
                associationId="assoc123",
                primary=True
                # Missing many required fields
            )
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "relationId" in error_fields
        assert "objectKey" in error_fields
        assert "recordId" in error_fields
        assert "fullName" in error_fields
        assert "email" in error_fields


class TestContact:
    """Test cases for Contact model (nested in opportunity)."""

    def test_contact_minimal(self):
        """Test creating Contact with required fields."""
        contact = Contact(
            id="contact123",
            name="John Doe",
            email="john@example.com"
        )
        
        assert contact.id == "contact123"
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"
        assert contact.companyName is None
        assert contact.phone is None
        assert contact.tags == []
        assert contact.score == []

    def test_contact_full(self):
        """Test Contact with all fields."""
        contact = Contact(
            id="contact123",
            name="Jane Smith",
            companyName="Tech Corp",
            email="jane@techcorp.com",
            phone="+9876543210",
            tags=["customer", "premium"],
            score=[{"type": "lead_score", "value": 85}]
        )
        
        assert contact.companyName == "Tech Corp"
        assert contact.phone == "+9876543210"
        assert len(contact.tags) == 2
        assert len(contact.score) == 1


class TestOpportunity:
    """Test cases for Opportunity model."""

    def test_opportunity_minimal(self):
        """Test creating Opportunity with minimal required fields."""
        now = datetime.now(timezone.utc)
        
        opp = Opportunity(
            id="opp123",
            name="Test Deal",
            pipelineId="pipe123",
            pipelineStageId="stage123",
            status=OpportunityStatus.OPEN,
            contactId="contact123",
            locationId="loc123",
            createdAt=now,
            updatedAt=now
        )
        
        assert opp.id == "opp123"
        assert opp.name == "Test Deal"
        assert opp.status == OpportunityStatus.OPEN
        assert opp.monetaryValue is None
        assert opp.notes is None
        assert opp.customFields == []

    def test_opportunity_full(self):
        """Test Opportunity with all common fields."""
        now = datetime.now(timezone.utc)
        contact = Contact(
            id="contact123",
            name="John Doe",
            email="john@example.com"
        )
        
        opp = Opportunity(
            id="opp123",
            name="Enterprise Deal",
            pipelineId="pipe123",
            pipelineStageId="stage456",
            pipelineStageUId="uid789",
            assignedTo="user123",
            status=OpportunityStatus.WON,
            source="Referral",
            lastStatusChangeAt=now,
            lastStageChangeAt=now,
            createdAt=now,
            updatedAt=now,
            contactId="contact123",
            contact=contact,
            monetaryValue=100000.00,
            locationId="loc123",
            notes="Important deal with enterprise features",
            customFields=[{"id": "field1", "value": "custom"}],
            followers=["user456", "user789"]
        )
        
        assert opp.monetaryValue == 100000.00
        assert opp.assignedTo == "user123"
        assert opp.source == "Referral"
        assert opp.notes == "Important deal with enterprise features"
        assert len(opp.followers) == 2
        assert opp.contact.name == "John Doe"

    def test_opportunity_datetime_parsing(self):
        """Test Opportunity datetime field parsing."""
        opp = Opportunity(
            id="opp123",
            name="Test Deal",
            pipelineId="pipe123",
            pipelineStageId="stage123",
            status=OpportunityStatus.OPEN,
            contactId="contact123",
            locationId="loc123",
            createdAt="2025-06-08T03:01:58.848Z",
            updatedAt="2025-06-09T10:30:00.000Z",
            lastStatusChangeAt="2025-06-07T15:00:00Z",
            lastStageChangeAt="2025-06-08T09:00:00Z"
        )
        
        assert isinstance(opp.createdAt, datetime)
        assert isinstance(opp.updatedAt, datetime)
        assert isinstance(opp.lastStatusChangeAt, datetime)
        assert isinstance(opp.lastStageChangeAt, datetime)
        
        # Check timezone awareness
        assert opp.createdAt.tzinfo is not None

    def test_opportunity_with_pipeline_info(self):
        """Test Opportunity with pipeline and stage details."""
        pipeline = Pipeline(id="pipe123", name="Sales Pipeline")
        stage = PipelineStage(id="stage123", name="Negotiation", position=3)
        
        opp = Opportunity(
            id="opp123",
            name="Test Deal",
            pipelineId="pipe123",
            pipelineStageId="stage123",
            status=OpportunityStatus.OPEN,
            contactId="contact123",
            locationId="loc123",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            pipeline=pipeline,
            stage=stage
        )
        
        assert opp.pipeline.name == "Sales Pipeline"
        assert opp.stage.name == "Negotiation"
        assert opp.stage.position == 3

    def test_opportunity_with_relations(self):
        """Test Opportunity with relations."""
        relations = [
            Relation(
                associationId="assoc1",
                relationId="rel1",
                primary=True,
                objectKey="contact",
                recordId="rec1",
                fullName="Primary Contact",
                contactName="Primary",
                email="primary@example.com"
            ),
            Relation(
                associationId="assoc2",
                relationId="rel2",
                primary=False,
                objectKey="contact",
                recordId="rec2",
                fullName="Secondary Contact",
                contactName="Secondary",
                email="secondary@example.com"
            )
        ]
        
        opp = Opportunity(
            id="opp123",
            name="Test Deal",
            pipelineId="pipe123",
            pipelineStageId="stage123",
            status=OpportunityStatus.OPEN,
            contactId="contact123",
            locationId="loc123",
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            relations=relations
        )
        
        assert len(opp.relations) == 2
        assert opp.relations[0].primary is True
        assert opp.relations[1].email == "secondary@example.com"

    def test_opportunity_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Opportunity(
                id="opp123",
                name="Test Deal"
                # Missing many required fields
            )
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "pipelineId" in error_fields
        assert "pipelineStageId" in error_fields
        assert "status" in error_fields
        assert "contactId" in error_fields
        assert "locationId" in error_fields
        assert "createdAt" in error_fields
        assert "updatedAt" in error_fields


class TestMeta:
    """Test cases for Meta model."""

    def test_meta_minimal(self):
        """Test creating Meta with required fields."""
        meta = Meta(
            total=100,
            currentPage=1
        )
        
        assert meta.total == 100
        assert meta.currentPage == 1
        assert meta.nextPageUrl is None
        assert meta.nextPage is None
        assert meta.prevPage is None

    def test_meta_with_pagination(self):
        """Test Meta with full pagination info."""
        meta = Meta(
            total=500,
            currentPage=3,
            nextPageUrl="/opportunities?page=4",
            startAfterId="opp123",
            startAfter=1234567890,
            nextPage="4",
            prevPage="2"
        )
        
        assert meta.total == 500
        assert meta.currentPage == 3
        assert meta.nextPageUrl == "/opportunities?page=4"
        assert meta.startAfterId == "opp123"
        assert meta.startAfter == 1234567890
        assert meta.nextPage == "4"
        assert meta.prevPage == "2"

    def test_meta_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Meta(total=100)  # Missing currentPage
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "currentPage" for e in errors)


class TestAggregations:
    """Test cases for Aggregations model."""

    def test_aggregations_empty(self):
        """Test Aggregations with empty data."""
        agg = Aggregations()
        
        assert agg.pipelines == {}

    def test_aggregations_with_data(self):
        """Test Aggregations with pipeline data."""
        pipeline_data = {
            "pipe123": {
                "total": 50,
                "value": 250000,
                "stages": {
                    "stage1": {"count": 10, "value": 50000},
                    "stage2": {"count": 20, "value": 100000},
                    "stage3": {"count": 20, "value": 100000}
                }
            }
        }
        
        agg = Aggregations(pipelines=pipeline_data)
        
        assert "pipe123" in agg.pipelines
        assert agg.pipelines["pipe123"]["total"] == 50
        assert agg.pipelines["pipe123"]["stages"]["stage2"]["count"] == 20


class TestOpportunitySearchResult:
    """Test cases for OpportunitySearchResult model."""

    def test_search_result_empty(self):
        """Test OpportunitySearchResult with no results."""
        result = OpportunitySearchResult()
        
        assert result.opportunities == []
        assert result.meta is None
        assert result.aggregations is None
        assert result.total is None
        assert result.count == 0

    def test_search_result_with_opportunities(self):
        """Test OpportunitySearchResult with opportunities."""
        opportunities = [
            Opportunity(
                id="opp1",
                name="Deal 1",
                pipelineId="pipe123",
                pipelineStageId="stage123",
                status=OpportunityStatus.OPEN,
                contactId="contact1",
                locationId="loc123",
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc)
            ),
            Opportunity(
                id="opp2",
                name="Deal 2",
                pipelineId="pipe123",
                pipelineStageId="stage456",
                status=OpportunityStatus.WON,
                contactId="contact2",
                locationId="loc123",
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc)
            )
        ]
        
        meta = Meta(total=50, currentPage=1)
        
        result = OpportunitySearchResult(
            opportunities=opportunities,
            meta=meta
        )
        
        assert len(result.opportunities) == 2
        assert result.total == 50
        assert result.count == 2

    def test_search_result_with_aggregations(self):
        """Test OpportunitySearchResult with aggregations."""
        agg = Aggregations(
            pipelines={"pipe123": {"total": 25, "value": 125000}}
        )
        
        result = OpportunitySearchResult(
            opportunities=[],
            aggregations=agg
        )
        
        assert result.aggregations.pipelines["pipe123"]["total"] == 25


class TestOpportunitySearchFilters:
    """Test cases for OpportunitySearchFilters model."""

    def test_search_filters_all_optional(self):
        """Test that all search filters are optional."""
        filters = OpportunitySearchFilters()
        
        assert filters.pipelineId is None
        assert filters.pipelineStageId is None
        assert filters.assignedTo is None
        assert filters.status is None
        assert filters.contactId is None
        assert filters.startDate is None
        assert filters.endDate is None
        assert filters.query is None

    def test_search_filters_full(self):
        """Test OpportunitySearchFilters with all fields."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        filters = OpportunitySearchFilters(
            pipelineId="pipe123",
            pipelineStageId="stage456",
            assignedTo="user123",
            status=OpportunityStatus.OPEN,
            contactId="contact123",
            startDate=start,
            endDate=end,
            query="enterprise"
        )
        
        assert filters.pipelineId == "pipe123"
        assert filters.pipelineStageId == "stage456"
        assert filters.assignedTo == "user123"
        assert filters.status == OpportunityStatus.OPEN
        assert filters.contactId == "contact123"
        assert filters.startDate == start
        assert filters.endDate == end
        assert filters.query == "enterprise"

    def test_search_filters_partial(self):
        """Test OpportunitySearchFilters with partial fields."""
        filters = OpportunitySearchFilters(
            status=OpportunityStatus.WON,
            query="closed deals"
        )
        
        assert filters.status == OpportunityStatus.WON
        assert filters.query == "closed deals"
        assert filters.pipelineId is None
        assert filters.startDate is None