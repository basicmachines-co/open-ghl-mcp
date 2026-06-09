"""Models for GoHighLevel location custom fields and custom values"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CustomField(BaseModel):
    """GoHighLevel custom field definition (location-level)"""

    id: Optional[str] = None
    name: Optional[str] = None
    fieldKey: Optional[str] = None
    placeholder: Optional[str] = None
    dataType: Optional[str] = None  # TEXT, LARGE_TEXT, NUMERICAL, PHONE, etc.
    position: Optional[int] = None
    picklistOptions: Optional[List[str]] = None
    picklistImageOptions: Optional[List[str]] = None
    isAllowedCustomOption: Optional[bool] = None
    isMultiFileAllowed: Optional[bool] = None
    maxFileLimit: Optional[int] = None
    locationId: Optional[str] = None
    model: Optional[str] = None  # contact | opportunity

    # `model` is a literal API field; opt out of pydantic's protected namespace
    model_config = {"populate_by_name": True, "protected_namespaces": ()}


class CustomFieldCreate(BaseModel):
    """Model for creating a custom field"""

    name: str
    dataType: str
    placeholder: Optional[str] = None
    acceptedFormat: Optional[List[str]] = None  # for FILE_UPLOAD fields
    isMultipleFile: Optional[bool] = None
    maxNumberOfFiles: Optional[int] = None
    textBoxListOptions: Optional[List[Dict[str, Any]]] = None
    position: Optional[int] = None
    model: Optional[str] = None  # contact | opportunity

    model_config = {"protected_namespaces": ()}


class CustomFieldUpdate(BaseModel):
    """Model for updating a custom field"""

    name: str
    placeholder: Optional[str] = None
    acceptedFormat: Optional[List[str]] = None
    isMultipleFile: Optional[bool] = None
    maxNumberOfFiles: Optional[int] = None
    textBoxListOptions: Optional[List[Dict[str, Any]]] = None
    position: Optional[int] = None
    model: Optional[str] = None

    model_config = {"protected_namespaces": ()}


class CustomFieldList(BaseModel):
    """Response model for a list of custom fields"""

    customFields: List[CustomField]
    count: int


class CustomValue(BaseModel):
    """GoHighLevel custom value (location-level key/value)"""

    id: Optional[str] = None
    name: Optional[str] = None
    fieldKey: Optional[str] = None
    value: Optional[str] = None
    locationId: Optional[str] = None

    model_config = {"populate_by_name": True}


class CustomValueCreate(BaseModel):
    """Model for creating a custom value"""

    name: str
    value: str


class CustomValueUpdate(BaseModel):
    """Model for updating a custom value"""

    name: str
    value: str


class CustomValueList(BaseModel):
    """Response model for a list of custom values"""

    customValues: List[CustomValue]
    count: int
