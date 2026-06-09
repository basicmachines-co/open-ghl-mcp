"""Custom fields and custom values client for GoHighLevel API v2"""

from typing import Optional

from .base import BaseGoHighLevelClient
from ..models.custom_field import (
    CustomField,
    CustomFieldCreate,
    CustomFieldUpdate,
    CustomFieldList,
    CustomValue,
    CustomValueCreate,
    CustomValueUpdate,
    CustomValueList,
)


class CustomFieldsClient(BaseGoHighLevelClient):
    """Client for location-level custom fields and custom values endpoints"""

    # --- Custom Fields ---

    async def get_custom_fields(
        self, location_id: str, model: Optional[str] = None
    ) -> CustomFieldList:
        """Get all custom fields for a location

        Args:
            location_id: The location to fetch custom fields for
            model: Optional filter - "contact", "opportunity", or "all"
        """
        params = {}
        if model:
            params["model"] = model
        response = await self._request(
            "GET",
            f"/locations/{location_id}/customFields",
            params=params or None,
            location_id=location_id,
        )
        data = response.json()
        fields = [CustomField(**c) for c in data.get("customFields", [])]
        return CustomFieldList(customFields=fields, count=len(fields))

    async def get_custom_field(
        self, custom_field_id: str, location_id: str
    ) -> CustomField:
        """Get a specific custom field by ID"""
        response = await self._request(
            "GET",
            f"/locations/{location_id}/customFields/{custom_field_id}",
            location_id=location_id,
        )
        data = response.json()
        return CustomField(**data.get("customField", data))

    async def create_custom_field(
        self, location_id: str, field: CustomFieldCreate
    ) -> CustomField:
        """Create a new custom field in a location"""
        response = await self._request(
            "POST",
            f"/locations/{location_id}/customFields",
            json=field.model_dump(exclude_none=True),
            location_id=location_id,
        )
        data = response.json()
        return CustomField(**data.get("customField", data))

    async def update_custom_field(
        self, custom_field_id: str, location_id: str, updates: CustomFieldUpdate
    ) -> CustomField:
        """Update an existing custom field"""
        response = await self._request(
            "PUT",
            f"/locations/{location_id}/customFields/{custom_field_id}",
            json=updates.model_dump(exclude_none=True),
            location_id=location_id,
        )
        data = response.json()
        return CustomField(**data.get("customField", data))

    async def delete_custom_field(self, custom_field_id: str, location_id: str) -> bool:
        """Delete a custom field"""
        response = await self._request(
            "DELETE",
            f"/locations/{location_id}/customFields/{custom_field_id}",
            location_id=location_id,
        )
        data = response.json() if response.content else {}
        # API returns {"succeded": true} (note their spelling)
        return bool(data.get("succeded", response.status_code in (200, 201)))

    # --- Custom Values ---

    async def get_custom_values(self, location_id: str) -> CustomValueList:
        """Get all custom values for a location"""
        response = await self._request(
            "GET",
            f"/locations/{location_id}/customValues",
            location_id=location_id,
        )
        data = response.json()
        values = [CustomValue(**c) for c in data.get("customValues", [])]
        return CustomValueList(customValues=values, count=len(values))

    async def get_custom_value(
        self, custom_value_id: str, location_id: str
    ) -> CustomValue:
        """Get a specific custom value by ID"""
        response = await self._request(
            "GET",
            f"/locations/{location_id}/customValues/{custom_value_id}",
            location_id=location_id,
        )
        data = response.json()
        return CustomValue(**data.get("customValue", data))

    async def create_custom_value(
        self, location_id: str, value: CustomValueCreate
    ) -> CustomValue:
        """Create a new custom value in a location"""
        response = await self._request(
            "POST",
            f"/locations/{location_id}/customValues",
            json=value.model_dump(exclude_none=True),
            location_id=location_id,
        )
        data = response.json()
        return CustomValue(**data.get("customValue", data))

    async def update_custom_value(
        self, custom_value_id: str, location_id: str, updates: CustomValueUpdate
    ) -> CustomValue:
        """Update an existing custom value"""
        response = await self._request(
            "PUT",
            f"/locations/{location_id}/customValues/{custom_value_id}",
            json=updates.model_dump(exclude_none=True),
            location_id=location_id,
        )
        data = response.json()
        return CustomValue(**data.get("customValue", data))

    async def delete_custom_value(self, custom_value_id: str, location_id: str) -> bool:
        """Delete a custom value"""
        response = await self._request(
            "DELETE",
            f"/locations/{location_id}/customValues/{custom_value_id}",
            location_id=location_id,
        )
        data = response.json() if response.content else {}
        return bool(data.get("succeded", response.status_code in (200, 201)))
