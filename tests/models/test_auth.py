"""Tests for the models.auth module."""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from src.models.auth import TokenResponse, LocationTokenResponse, StoredToken


class TestTokenResponse:
    """Test cases for TokenResponse model."""

    def test_token_response_creation(self):
        """Test creating a TokenResponse with all fields."""
        response = TokenResponse(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="contacts.readonly",
            userType="Company",
            userId="user123"
        )
        
        assert response.access_token == "test_access_token"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
        assert response.refresh_token == "test_refresh_token"
        assert response.scope == "contacts.readonly"
        assert response.userType == "Company"
        assert response.userId == "user123"

    def test_token_response_optional_user_id(self):
        """Test that userId is optional."""
        response = TokenResponse(
            access_token="test_access_token",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="contacts.readonly",
            userType="Company"
        )
        
        assert response.userId is None

    def test_token_response_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TokenResponse(
                access_token="test_access_token",
                # Missing expires_in, refresh_token, scope, userType
            )
        
        errors = exc_info.value.errors()
        error_fields = [e["loc"][0] for e in errors]
        assert "expires_in" in error_fields
        assert "refresh_token" in error_fields
        assert "scope" in error_fields
        assert "userType" in error_fields


class TestLocationTokenResponse:
    """Test cases for LocationTokenResponse model."""

    def test_location_token_response_creation(self):
        """Test creating a LocationTokenResponse with all fields."""
        response = LocationTokenResponse(
            access_token="location_access_token",
            token_type="Bearer",
            expires_in=7200,
            refresh_token="location_refresh_token",
            scope="locations.readonly",
            userId="user123",
            userType="Location",
            locationId="loc123"
        )
        
        assert response.access_token == "location_access_token"
        assert response.expires_in == 7200
        assert response.locationId == "loc123"
        assert response.userType == "Location"

    def test_location_token_response_optional_refresh_token(self):
        """Test that refresh_token is optional for location tokens."""
        response = LocationTokenResponse(
            access_token="location_access_token",
            expires_in=7200,
            scope="locations.readonly",
            userId="user123",
            locationId="loc123"
        )
        
        assert response.refresh_token is None
        assert response.userType == "Location"  # Default value

    def test_location_token_response_required_location_id(self):
        """Test that locationId is required."""
        with pytest.raises(ValidationError) as exc_info:
            LocationTokenResponse(
                access_token="location_access_token",
                expires_in=7200,
                scope="locations.readonly",
                userId="user123"
                # Missing locationId
            )
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "locationId" for e in errors)


class TestStoredToken:
    """Test cases for StoredToken model."""

    def test_stored_token_creation(self):
        """Test creating a StoredToken directly."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token = StoredToken(
            access_token="stored_access_token",
            refresh_token="stored_refresh_token",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full_access",
            user_type="Company"
        )
        
        assert token.access_token == "stored_access_token"
        assert token.refresh_token == "stored_refresh_token"
        assert token.expires_at == expires_at
        assert token.user_type == "Company"

    def test_from_token_response(self):
        """Test creating StoredToken from TokenResponse."""
        response = TokenResponse(
            access_token="test_access_token",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="contacts.readonly",
            userType="Company"
        )
        
        before_creation = datetime.now(timezone.utc)
        stored_token = StoredToken.from_token_response(response)
        after_creation = datetime.now(timezone.utc)
        
        assert stored_token.access_token == response.access_token
        assert stored_token.refresh_token == response.refresh_token
        assert stored_token.scope == response.scope
        assert stored_token.user_type == response.userType
        
        # Check that expires_at is approximately correct
        expected_expiry = before_creation + timedelta(seconds=3600)
        assert stored_token.expires_at >= expected_expiry - timedelta(seconds=1)
        assert stored_token.expires_at <= after_creation + timedelta(seconds=3600)

    def test_is_expired_not_expired(self):
        """Test is_expired returns False for valid token."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token = StoredToken(
            access_token="token",
            refresh_token="refresh",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full",
            user_type="Company"
        )
        
        assert not token.is_expired()

    def test_is_expired_already_expired(self):
        """Test is_expired returns True for expired token."""
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        token = StoredToken(
            access_token="token",
            refresh_token="refresh",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full",
            user_type="Company"
        )
        
        assert token.is_expired()

    def test_is_expired_naive_datetime(self):
        """Test is_expired handles naive datetime by treating it as UTC."""
        # Create a naive datetime (no timezone info) that's in the future
        # Create it based on UTC time but remove timezone info
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        token = StoredToken(
            access_token="token",
            refresh_token="refresh",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full",
            user_type="Company"
        )
        
        # Should not be expired
        assert not token.is_expired()

    def test_needs_refresh_within_buffer(self):
        """Test needs_refresh returns True when within buffer time."""
        # Token expires in 4 minutes (within 5-minute buffer)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        token = StoredToken(
            access_token="token",
            refresh_token="refresh",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full",
            user_type="Company"
        )
        
        assert token.needs_refresh()  # Default 5-minute buffer

    def test_needs_refresh_outside_buffer(self):
        """Test needs_refresh returns False when outside buffer time."""
        # Token expires in 10 minutes (outside 5-minute buffer)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        token = StoredToken(
            access_token="token",
            refresh_token="refresh",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full",
            user_type="Company"
        )
        
        assert not token.needs_refresh()  # Default 5-minute buffer

    def test_needs_refresh_custom_buffer(self):
        """Test needs_refresh with custom buffer time."""
        # Token expires in 25 minutes
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=25)
        token = StoredToken(
            access_token="token",
            refresh_token="refresh",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full",
            user_type="Company"
        )
        
        # With 30-minute buffer, should need refresh
        assert token.needs_refresh(buffer_seconds=1800)  # 30 minutes
        
        # With 20-minute buffer, should not need refresh
        assert not token.needs_refresh(buffer_seconds=1200)  # 20 minutes

    def test_needs_refresh_naive_datetime(self):
        """Test needs_refresh handles naive datetime correctly."""
        # Create a naive datetime that expires in 4 minutes
        # Create it based on UTC time but remove timezone info
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=4)
        token = StoredToken(
            access_token="token",
            refresh_token="refresh",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full",
            user_type="Company"
        )
        
        # Should need refresh (within 5-minute buffer)
        assert token.needs_refresh()

    def test_expires_at_serialization(self):
        """Test that expires_at is serialized to ISO format."""
        expires_at = datetime(2025, 6, 16, 12, 0, 0, tzinfo=timezone.utc)
        token = StoredToken(
            access_token="token",
            refresh_token="refresh",
            token_type="Bearer",
            expires_at=expires_at,
            scope="full",
            user_type="Company"
        )
        
        # Test serialization
        dumped = token.model_dump()
        assert dumped["expires_at"] == "2025-06-16T12:00:00+00:00"
        
        # Test JSON serialization
        json_str = token.model_dump_json()
        assert "2025-06-16T12:00:00+00:00" in json_str