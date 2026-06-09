"""Custom field and custom value parameter classes for MCP tools"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class GetCustomFieldsParams(BaseModel):
    """Parameters for listing custom fields"""

    location_id: str = Field(
        ..., description="The location ID to list custom fields for"
    )
    model: Optional[str] = Field(
        None,
        description="Filter by model: 'contact', 'opportunity', or 'all'",
    )
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class GetCustomFieldParams(BaseModel):
    """Parameters for getting a single custom field"""

    custom_field_id: str = Field(..., description="The custom field ID to retrieve")
    location_id: str = Field(..., description="The location ID where the field exists")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class CreateCustomFieldParams(BaseModel):
    """Parameters for creating a custom field"""

    location_id: str = Field(..., description="The location ID to create the field in")
    name: str = Field(..., description="The display name of the custom field")
    data_type: str = Field(
        ...,
        description="Field data type, e.g. TEXT, LARGE_TEXT, NUMERICAL, PHONE, "
        "MONETORY, CHECKBOX, SINGLE_OPTIONS, MULTIPLE_OPTIONS, DATE, FILE_UPLOAD",
    )
    placeholder: Optional[str] = Field(None, description="Placeholder text")
    model: Optional[str] = Field(
        None, description="Object the field belongs to: 'contact' or 'opportunity'"
    )
    position: Optional[int] = Field(None, description="Display position/order")
    accepted_format: Optional[List[str]] = Field(
        None, description="Accepted file formats for FILE_UPLOAD fields (e.g. ['.pdf'])"
    )
    is_multiple_file: Optional[bool] = Field(
        None, description="Whether multiple files are allowed (FILE_UPLOAD)"
    )
    max_number_of_files: Optional[int] = Field(
        None, description="Max number of files allowed (FILE_UPLOAD)"
    )
    text_box_list_options: Optional[List[Dict[str, Any]]] = Field(
        None, description="Options for picklist/option-style fields"
    )
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class UpdateCustomFieldParams(BaseModel):
    """Parameters for updating a custom field"""

    custom_field_id: str = Field(..., description="The custom field ID to update")
    location_id: str = Field(..., description="The location ID where the field exists")
    name: str = Field(..., description="The display name of the custom field")
    placeholder: Optional[str] = Field(None, description="Placeholder text")
    model: Optional[str] = Field(
        None, description="Object the field belongs to: 'contact' or 'opportunity'"
    )
    position: Optional[int] = Field(None, description="Display position/order")
    accepted_format: Optional[List[str]] = Field(
        None, description="Accepted file formats for FILE_UPLOAD fields"
    )
    is_multiple_file: Optional[bool] = Field(
        None, description="Whether multiple files are allowed (FILE_UPLOAD)"
    )
    max_number_of_files: Optional[int] = Field(
        None, description="Max number of files allowed (FILE_UPLOAD)"
    )
    text_box_list_options: Optional[List[Dict[str, Any]]] = Field(
        None, description="Options for picklist/option-style fields"
    )
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class DeleteCustomFieldParams(BaseModel):
    """Parameters for deleting a custom field"""

    custom_field_id: str = Field(..., description="The custom field ID to delete")
    location_id: str = Field(..., description="The location ID where the field exists")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class GetCustomValuesParams(BaseModel):
    """Parameters for listing custom values"""

    location_id: str = Field(
        ..., description="The location ID to list custom values for"
    )
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class GetCustomValueParams(BaseModel):
    """Parameters for getting a single custom value"""

    custom_value_id: str = Field(..., description="The custom value ID to retrieve")
    location_id: str = Field(..., description="The location ID where the value exists")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class CreateCustomValueParams(BaseModel):
    """Parameters for creating a custom value"""

    location_id: str = Field(..., description="The location ID to create the value in")
    name: str = Field(..., description="The name of the custom value")
    value: str = Field(..., description="The value to store")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class UpdateCustomValueParams(BaseModel):
    """Parameters for updating a custom value"""

    custom_value_id: str = Field(..., description="The custom value ID to update")
    location_id: str = Field(..., description="The location ID where the value exists")
    name: str = Field(..., description="The name of the custom value")
    value: str = Field(..., description="The value to store")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class DeleteCustomValueParams(BaseModel):
    """Parameters for deleting a custom value"""

    custom_value_id: str = Field(..., description="The custom value ID to delete")
    location_id: str = Field(..., description="The location ID where the value exists")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )
