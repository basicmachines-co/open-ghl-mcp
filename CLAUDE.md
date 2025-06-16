# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server for the GoHighLevel 2.0 API using FastMCP. The server bridges AI models and the GoHighLevel API.

## GoHighLevel API Documentation
The official API docs are at https://github.com/GoHighLevel/api-v2-docs.

Always use the official API docs at https://github.com/GoHighLevel/api-v2-docs to understand the API and prefer this resource over any other documentation.

Only use API v2. Do not use API v1 or refer to API v1 documentation.

## Coding
- **Imports** - Place all imports at the top of the file

## Testing
If you need to test the MCP server with real GoHighLevel accounts, check for TESTING_INSTRUCTIONS.md in the project root. This file contains specific testing accounts and instructions but is not committed to the repository.

You can use `curl` to test the API directly and evaluate what is returned to help you troubleshoot.

When using `curl` be sure to:
- include the correct version header, which is most likely `--header 'Version: 2021-07-28'`
- use the correct content type: --header 'Accept: application/json'

- **Framework**: FastMCP (Python)
- **Target API**: GoHighLevel 2.0
- **Primary Language**: Python

## Common Commands

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=src

# Run linting
flake8 src/ tests/

# Run type checking
mypy src/

# Start the MCP server
python -m src.main
```

## Architecture

The MCP server follows a modular architecture:

0. **Coding** (*.py):
   - When files exceed 350 lines suggest refactoring. Try to keep files to a reasonable size.
   - Check Basic Memory for help with documentation
   - Keep in mind that the documentation is best effort. Use `curl` to validate the actual API request/response exchange.
   - This project is maintained with git and GitHub at https://github.com/basicmachines-co/open-ghl-mcp so it's not necessary to create copies or backup files
   - All import directives should be grouped together at the top of the file

1. **OAuth Service** (`src/services/oauth.py`):
   - Dual-mode authentication: standard
   - Single-mode authentication: custom
   - Handles OAuth 2.0 flow with GoHighLevel
   - Manages agency and location token exchange
   - Automatic token refresh and caching
   - Browser-based authorization flow (standard mode)
   - Manual authentication (custom mode)
   - Each endpoint follows the same pattern requiring location tokens for access

2. **API Client** (`src/api/client.py`):
   - Async HTTP client for GoHighLevel API v2
   - Automatic location token usage for contact operations
   - Consistent error handling and response parsing

3. **MCP Server** (`src/main.py`):
   - FastMCP-based implementation
   - Tools for CRUD operations on contacts
   - Resources for listing and viewing contacts
   - Support for custom access tokens per request

4. **Models** (`src/models/`):
   - Pydantic models for contacts and authentication
   - Request/response validation
   - Type safety throughout the codebase

5. **CI/CD** (`.github/workflows/test.yml`)
   - Git for source control
   - GitHub Actions for CI/CD
   - Tests run on every push

6. **Testing** (`tests/*`)
   - IMPORTANT: If you need to change the auth configuration do not destroy a valid config. Instead, move it somewhere it can be moved back
   - Use the virtual environment when testing: `$ source .venv/bin/activate && python`
   - Put tests in the tests/ directory and mirror the folder structure in src/ with a matching test file for each source file
   - Run all of the checks with the tests: `uv run black src/ tests/ && uv run flake8 src/ tests/ && uv run mypy src/ --ignore-missing-imports && uv run pytest`
   - To test interactive server startup flows (like setup wizards), use piped input: `echo -e "2\ny\nclient_id\nclient_secret" | uv run python -m src.main`
     - The server detects if it's running interactively vs being managed by Claude Desktop
     - Interactive mode shows setup wizards and configuration instructions
     - When run by Claude Desktop, it operates as an MCP server without interactive prompts
   - When searching for the Claude Desktop config check the default folder paths before searching the entire disk
   - Remember when adding endpoints to add the correct scopes to ALL_SCOPES in ./services/oauth.py

## Key Implementation Details

### Authentication Flow

#### Standard Mode (Default)
1. User authenticates through Basic Machines Marketplace App
2. Basic Machines handles OAuth for this MCP server

#### Custom Mode
1. User creates their own Marketplace App and credentials
2. User creates a .env file with their credentials
3. User runs the MCP server with the .env file
4. User can use the MCP server with their own credentials

### API Quirks
- Location token endpoint returns 201 (not 200)
- Contact endpoints require locationId even with location token
- Skip parameter should be omitted if 0
- Duplicate contacts return 400 with details

### Adding New Endpoints
1. Add models to `src/models/`
2. Add client methods to `src/api/client.py` (remember location_id parameter)
3. Add MCP tools/resources to `src/main.py`
4. Test with both agency and location tokens

### Type Definitions
1. Refer to the official API docs at https://highlevel.stoplight.io/docs/integrations/ to understand the API and correctly implement MCP tools and resources.
2. The official API docs define Schemas that should be used as a reference.
3. When adding new MCP tools and resources use the schemas from the API docs to define the types for the MCP server.
4. The schema definitions in the documentation should be considered "best effort" and may not be complete or accurate, but should always be used as a starting point.


## Critical OAuth Implementation Lessons

### Two-Step Authentication Required
- Initial OAuth provides agency/company token
- Must exchange for location token to access contacts: POST `/oauth/locationToken`
- Include both `companyId` (from JWT) and `locationId` in request

### OAuth Endpoints
- Use `/oauth/chooselocation` for authorization (NOT `/oauth/authorize`)
- Token exchange: `https://services.leadconnectorhq.com/oauth/token`
- Add `user_type: "Location"` to token exchange request

### Common Pitfalls to Avoid
- Location token endpoint returns 201 (not 200) - handle both
- Always include `locationId` in API calls even with location token
- Omit `skip` parameter if value is 0 (causes 422 error)
- Extract company ID from JWT dynamically - never hardcode
- Test data needs unique identifiers (use timestamps) to avoid duplicate errors

### MCP Pattern for New Resources
```python
# Tools need location_id parameter
class YourToolParams(BaseModel):
    location_id: str = Field(..., description="The location ID")
    # ... other fields
    access_token: Optional[str] = Field(None, description="Optional access token")

# Client methods need location_id
async def your_method(self, resource_id: str, location_id: str):
    response = await self._request(
        "GET",
        f"/endpoint/{resource_id}",
        location_id=location_id  # This triggers location token usage
    )
```

## Message System Implementation Guide

### Critical: Message Type System
The API uses different formats for sending vs reading messages:
- **Sending messages**: Use string values `"SMS"`, `"Email"`, `"WhatsApp"`, `"IG"`, `"FB"`, `"Custom"`, `"Live_Chat"` in the `type` field
- **Reading messages**: API returns:
  - `type`: Numeric code (e.g., 1 for SMS, 2 for Email, 28 for activities)
  - `messageType`: String with TYPE_ prefix (e.g., "TYPE_SMS", "TYPE_EMAIL", "TYPE_ACTIVITY_OPPORTUNITY")
- **Model design**: Support both the sending format strings and reading format strings in enums

### Email Message Structure
Email messages require specific fields (NOT the generic "message" field):
```json
{
  "type": "Email",
  "conversationId": "...",
  "contactId": "...",
  "html": "<p>HTML content</p>",     // REQUIRED
  "subject": "Email subject",        // REQUIRED
  "text": "Plain text version"       // OPTIONAL but recommended
}
```

### SMS Message Structure
```json
{
  "type": "SMS",
  "conversationId": "...",
  "contactId": "...",
  "message": "SMS content",          // REQUIRED
  "phone": "+1234567890"             // REQUIRED
}
```

### Known API Response Patterns
- **Conversations search endpoint**: `/conversations/search` (not `/conversations`)
- **Messages response structure**: Nested as `data.messages.messages`
- **Send message response**: Returns `{conversationId, messageId}` only (not full message)
- **Message body field**: Can be missing for activity/system messages
- **Message status values**: Include non-standard values like `"voicemail"`

### Common API Error Patterns
- `"Missing phone number"` - Wrong field name or missing required field
- `"There is no message or attachments"` - Wrong content field for message type
- `"type must be a valid enum value"` - Using wrong string format for type

### Field Naming Gotchas
- Phone field: Sometimes `phone`, sometimes `phoneNumber`
- Email content: Use `html` not `message`, `body`, or `content`
- Always test with real API calls - documentation may not reflect actual requirements

### Documentation Gotchas
- The API docs are not always accurate, but should be used as a starting point.

## Opportunities System Implementation Guide

### Critical: Opportunity Management System
The MCP server now includes full support for GoHighLevel's opportunities (sales pipeline) system:

#### Core Opportunity Endpoints
- **GET /opportunities/search**: List opportunities with filters
- **GET /opportunities/{id}**: Get specific opportunity
- **POST /opportunities**: Create new opportunity
- **PUT /opportunities/{id}**: Update opportunity
- **DELETE /opportunities/{id}**: Delete opportunity
- **PUT /opportunities/{id}/status**: Update opportunity status

#### Pipeline Management Endpoints
- **GET /pipelines**: List all pipelines for location
- **GET /pipelines/{id}**: Get specific pipeline
- **GET /pipelines/{id}/stages**: Get stages for pipeline

### Opportunity JSON Structure
Standard opportunity object with required fields:
```json
{
  "pipelineId": "required-pipeline-id",
  "locationId": "required-location-id",
  "name": "Opportunity Name",
  "pipelineStageId": "required-stage-id",
  "status": "open|won|lost|abandoned",
  "contactId": "required-contact-id",
  "monetaryValue": 5000.00,
  "assignedTo": "user-id",
  "source": "Lead source",
  "notes": "Opportunity notes"
}
```

### MCP Tools Available
- `get_opportunities`: Search opportunities with filtering
- `get_opportunity`: Get single opportunity by ID
- `create_opportunity`: Create new opportunity
- `update_opportunity`: Update existing opportunity
- `delete_opportunity`: Delete opportunity
- `update_opportunity_status`: Change opportunity status
- `get_pipelines`: List location pipelines
- `get_pipeline`: Get specific pipeline
- `get_pipeline_stages`: Get pipeline stages

### MCP Resources Available
- `opportunities://{location_id}`: Browse all opportunities for location
- `opportunity://{location_id}/{opportunity_id}`: View single opportunity
- `pipelines://{location_id}`: Browse all pipelines with stages

### Key Implementation Details

#### Required Fields for Opportunity Creation
1. **pipelineId**: Must be valid pipeline for the location
2. **locationId**: Location where opportunity exists
3. **name**: Opportunity name/title
4. **pipelineStageId**: Must be valid stage within the pipeline
5. **contactId**: Must be existing contact in the location

#### Opportunity Status Flow
- **open**: Active opportunity (default)
- **won**: Successfully closed
- **lost**: Opportunity lost to competitor/no decision
- **abandoned**: Opportunity abandoned/invalid

#### Pipeline & Stage Management
- Pipelines contain multiple stages in order
- Each stage has position number for ordering
- Opportunities move through stages in pipeline
- Stage changes are tracked with timestamps

### Common API Error Patterns
- **"Pipeline not found"**: Invalid pipelineId for location
- **"Stage not found"**: Invalid pipelineStageId for pipeline
- **"Contact not found"**: Invalid contactId for location
- **"Missing required field"**: pipelineId, locationId, name, etc.

### Field Naming Gotchas
- Use `pipelineId` not `pipeline_id`
- Use `pipelineStageId` not `stage_id` or `stageId`
- Use `monetaryValue` not `value` or `amount`
- Use `assignedTo` not `assigned_to` or `userId`

### Business Logic Notes
- Opportunities track sales progress through pipeline stages
- Monetary values should be stored as numbers (not strings)
- Stage changes update `lastStageChangeAt` timestamp
- Status changes update `lastStatusChangeAt` timestamp
- Pipeline reports aggregate opportunities by stage and status

### OAuth Scopes Required
The following scopes are required for opportunities functionality:
- `opportunities.readonly` - Required for GET operations
- `opportunities.write` - Required for CREATE, UPDATE, DELETE operations

**IMPORTANT**: If you get authorization errors, you need to re-authorize your GoHighLevel app with the updated scopes. Delete `config/tokens.json` and run the MCP server again to trigger the OAuth flow with the new scopes.

### Datetime Parsing
The opportunities API returns datetime strings in ISO 8601 format with 'Z' suffix (e.g., `"2025-06-08T03:01:58.848Z"`). The Pydantic models automatically parse these into timezone-aware Python datetime objects. This resolves the datetime comparison errors that were previously occurring in Claude Desktop.

## Calendar & Appointment System Implementation Guide

### Critical: Calendar Management System
The MCP server now includes full support for GoHighLevel's calendar and appointment booking system:

#### Core Calendar Endpoints
- **GET /calendars/**: List all calendars for location
- **GET /calendars/{id}**: Get specific calendar details
- **GET /calendars/events**: List appointments/events with filtering
- **GET /calendars/events/appointments/{id}**: Get specific appointment
- **POST /calendars/events/appointments**: Create new appointment
- **PUT /calendars/events/appointments/{id}**: Update appointment
- **DELETE /calendars/events/{id}**: Delete appointment
- **GET /calendars/{id}/free-slots**: Get available time slots

### Calendar JSON Structure
Standard calendar object structure:
```json
{
  "id": "calendar-id",
  "locationId": "location-id",
  "name": "Calendar Name",
  "description": "Calendar description",
  "widgetType": "default",
  "widgetSlug": "calendar-slug",
  "appointmentTitle": "Appointment Title Template"
}
```

### Appointment JSON Structure
Standard appointment object with required fields:
```json
{
  "id": "appointment-id",
  "calendarId": "required-calendar-id",
  "locationId": "required-location-id",
  "contactId": "required-contact-id",
  "startTime": "2025-06-08T10:00:00Z",
  "endTime": "2025-06-08T11:00:00Z",
  "title": "Appointment Title",
  "appointmentStatus": "confirmed",
  "assignedUserId": "user-id",
  "notes": "Appointment notes",
  "address": "Appointment location"
}
```

### MCP Tools Available
- `get_calendars`: List all calendars for location
- `get_calendar`: Get single calendar by ID
- `get_appointments`: Search appointments/events with filtering
- `get_appointment`: Get single appointment by ID
- `create_appointment`: Create new appointment
- `update_appointment`: Update existing appointment
- `delete_appointment`: Delete appointment
- `get_free_slots`: Get available time slots for booking

### MCP Resources Available
- `calendars://{location_id}`: Browse all calendars for location
- `calendar://{location_id}/{calendar_id}`: View single calendar details
- `appointments://{location_id}/{calendar_id}`: Browse all appointments for calendar
- `appointment://{location_id}/{appointment_id}`: View single appointment

### Key Implementation Details

#### Required Fields for Appointment Creation
1. **calendarId**: Must be valid calendar for the location
2. **locationId**: Location where appointment exists
3. **contactId**: Must be existing contact in the location
4. **startTime**: Appointment start time (ISO 8601 format)
5. **endTime**: Appointment end time (ISO 8601 format)

#### Appointment Status Flow
- **confirmed**: Appointment is confirmed (default)
- **showed**: Contact showed up for appointment
- **noshow**: Contact did not show up
- **cancelled**: Appointment was cancelled
- **rescheduled**: Appointment was rescheduled

#### Time Slot Management
- Free slots endpoint shows available booking times
- Considers existing appointments and calendar availability
- Supports timezone-aware scheduling
- Can filter by date ranges

### Common API Error Patterns
- **"Calendar not found"**: Invalid calendarId for location
- **"Contact not found"**: Invalid contactId for location
- **"Invalid time slot"**: Appointment time conflicts or outside availability
- **"Missing required field"**: calendarId, locationId, contactId, startTime, endTime

### Field Naming Gotchas
- Use `calendarId` not `calendar_id`
- Use `contactId` not `contact_id`
- Use `startTime`/`endTime` not `start_time`/`end_time`
- Use `appointmentStatus` not `status`
- Use `assignedUserId` not `assigned_to` or `userId`

### API Endpoint Structure Lessons
Based on curl testing with actual GoHighLevel API:

#### Corrected Endpoint Patterns
- **List Calendars**: `GET /calendars/?locationId={locationId}` (requires locationId parameter)
- **List Events**: `GET /calendars/events` (not `/calendars/events/appointments`)
- **Event Parameters**: Use `startTime`/`endTime` instead of `startDate`/`endDate`
- **Response Structure**: Events returned in `events` array, not `appointments`

#### Authentication Requirements
- All endpoints require `Authorization: Bearer <token>` header
- All endpoints require `Version: 2021-07-28` header
- Location-specific operations require location tokens
- Invalid tokens return 401 "Invalid JWT" responses

### Business Logic Notes
- Appointments are tied to specific calendars within locations
- Calendar availability rules determine bookable time slots
- Appointment conflicts are automatically detected
- Time zones are handled consistently across API
- Appointment reminders and notifications are managed separately

### OAuth Scopes Required
The following scopes are required for calendar functionality:
- `calendars.readonly` - Required for GET operations
- `calendars.write` - Required for CREATE, UPDATE, DELETE operations
- `calendars/events.readonly` - Required for reading appointments/events
- `calendars/events.write` - Required for creating/updating appointments

**IMPORTANT**: If you get authorization errors, you need to re-authorize your GoHighLevel app with the updated scopes. Delete `config/tokens.json` and run the MCP server again to trigger the OAuth flow with the new scopes.

### Datetime Handling
The calendar API uses ISO 8601 datetime format with timezone information. The Pydantic models automatically handle conversion between ISO strings and Python datetime objects. Always provide timezone-aware datetimes for appointment scheduling to avoid conflicts.

#### Important: Timezone Format for Appointments
When creating appointments, the GoHighLevel API requires timezone-aware ISO format strings. Common formats:
- **Central Time**: `2025-06-09T11:00:00-05:00` (CST) or `2025-06-09T11:00:00-06:00` (CDT)
- **Eastern Time**: `2025-06-09T11:00:00-04:00` (EDT) or `2025-06-09T11:00:00-05:00` (EST)
- **Pacific Time**: `2025-06-09T11:00:00-07:00` (PDT) or `2025-06-09T11:00:00-08:00` (PST)
- **UTC**: `2025-06-09T16:00:00Z` or `2025-06-09T16:00:00+00:00`

**Note**: When you get "slot no longer available" errors, check that your datetime format includes the timezone offset.

## Forms & Submissions System Implementation Guide

### Critical: Forms Management System
The MCP server now includes full support for GoHighLevel's forms and submissions system:

#### Core Forms Endpoints
- **GET /forms**: List all forms for location
- **GET /forms/{id}**: Get specific form with field structure
- **GET /forms/{id}/submissions**: Get submissions for specific form
- **GET /forms/submissions**: Get all form submissions with filtering
- **POST /forms/submit**: Submit form data (unauthenticated, mimics website)
- **POST /forms/upload-custom-files**: Upload files to custom fields

### Form JSON Structure
Standard form object structure:
```json
{
  "id": "form-id",
  "name": "Contact Form",
  "locationId": "location-id",
  "description": "Lead generation form",
  "isActive": true,
  "fields": [
    {
      "id": "firstName",
      "label": "First Name",
      "type": "text",
      "required": true
    },
    {
      "id": "custom_field_abc123",
      "label": "Interest Level",
      "type": "dropdown",
      "options": ["Low", "Medium", "High"],
      "required": false
    }
  ],
  "thankYouMessage": "Thanks for submitting!",
  "redirectUrl": "https://example.com/thank-you"
}
```

### Form Submission Structure
```json
{
  "formId": "form-id",
  "locationId": "location-id",
  "firstName": "John",
  "lastName": "Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "custom_field_abc123": "High"
}
```

### MCP Tools Available
- `get_forms`: List all forms for location (returns only id, name, locationId)
- `get_all_form_submissions`: Get all submissions across all forms with filtering
- `upload_form_file`: Upload file to custom field (requires contact ID)

**NOTE**: The following endpoints are NOT supported by the GoHighLevel API:
- `GET /forms/{id}` - Returns 401 "This route is not yet supported by the IAM Service"
- `GET /forms/{id}/submissions` - Returns 404 Not Found
- `POST /forms/submit` - Returns 401 Unauthorized (both authenticated and unauthenticated versions)

### Key Implementation Details

#### Form Submission Approach
- **Unauthenticated endpoint**: Uses `https://backend.leadconnectorhq.com/forms/submit`
- **Mimics real visitors**: No API token required, just like website forms
- **Automatic contact creation**: Submissions create/update contacts
- **Attribution tracking**: Captures lead source data

#### Custom Fields
- Custom fields have random IDs (e.g., "IvYfCvMkhGap6sTe1Uql")
- Use `get_form` to discover field IDs and structure
- Pass custom field values in the `custom_fields` dictionary
- Custom fields are flattened into the submission data

#### File Uploads
- Files are passed as base64-encoded strings
- Supports multipart form data upload
- Requires contact ID and field ID
- Common for document collection in forms

### Common API Error Patterns
- **"Form not found"**: Invalid formId for location
- **"Required field missing"**: Check form structure for required fields
- **"Invalid custom field"**: Verify field ID exists in form
- **"File too large"**: Check file size limits

### Field Types
- `text`: Plain text input
- `email`: Email with validation
- `phone`: Phone number with formatting
- `textarea`: Multi-line text
- `dropdown`: Select with options
- `checkbox`: Single checkbox
- `radio`: Radio button group
- `file`: File upload field
- `date`: Date picker
- `number`: Numeric input

### Business Logic Notes
- Forms are the primary lead generation tool in GoHighLevel
- Every submission creates an activity in the contact timeline
- Forms can trigger automation workflows
- Custom fields enable business-specific data collection
- Form analytics track conversion rates

### OAuth Scopes Required
The following scopes are required for forms functionality:
- `forms.readonly` - Required for GET operations
- `forms.write` - Required for CREATE operations and file uploads

**IMPORTANT**: If you get authorization errors, you need to re-authorize your GoHighLevel app with the updated scopes. Delete `config/tokens.json` and run the MCP server again to trigger the OAuth flow with the new scopes.

### Testing Forms
To test form submission like a website visitor would:
```python
# Example: "Claude, test form ABC123 with name John Doe and email john@example.com"
# 1. First get the form structure
form = await get_form(form_id="ABC123", location_id="location_id")

# 2. Submit the form
result = await submit_form(
    form_id="ABC123",
    location_id="location_id",
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    custom_fields={"field_id": "value"}
)
```
