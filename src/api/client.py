"""Main GoHighLevel API v2 client with composition pattern"""

from typing import Any, Dict, Optional, List
from datetime import date

from ..services.oauth import OAuthService
from ..models.contact import Contact, ContactCreate, ContactUpdate, ContactList
from ..models.conversation import (
    Conversation,
    ConversationCreate,
    ConversationList,
    Message,
    MessageCreate,
    MessageList,
)
from ..models.opportunity import (
    Opportunity,
    OpportunityCreate,
    OpportunityUpdate,
    OpportunitySearchResult,
    OpportunitySearchFilters,
    Pipeline,
)
from ..models.calendar import (
    Appointment,
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentList,
    Calendar,
    CalendarList,
    FreeSlotsResult,
)
from ..models.form import (
    FormList,
    FormSubmissionList,
    FormFileUploadRequest,
)
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

from ..models.notes_tasks import (
    Note,
    NoteCreate,
    NoteUpdate,
    NoteList,
    Task,
    TaskCreate,
    TaskUpdate,
    TaskList,
)
from ..models.user import User, UserCreate, UserUpdate, UserList
from ..models.workflow import WorkflowList

from .contacts import ContactsClient
from .conversations import ConversationsClient
from .opportunities import OpportunitiesClient
from .calendars import CalendarsClient
from .forms import FormsClient
from .custom_fields import CustomFieldsClient
from .notes_tasks import NotesTasksClient
from .users import UsersClient
from .workflows import WorkflowsClient


class GoHighLevelClient:
    """Main client for interacting with GoHighLevel API v2

    Uses composition pattern to delegate to specialized endpoint clients
    while maintaining the same public interface for backward compatibility.
    """

    def __init__(self, oauth_service: OAuthService):
        self.oauth_service = oauth_service

        # Initialize specialized clients
        self._contacts = ContactsClient(oauth_service)
        self._conversations = ConversationsClient(oauth_service)
        self._opportunities = OpportunitiesClient(oauth_service)
        self._calendars = CalendarsClient(oauth_service)
        self._forms = FormsClient(oauth_service)
        self._custom_fields = CustomFieldsClient(oauth_service)
        self._notes_tasks = NotesTasksClient(oauth_service)
        self._users = UsersClient(oauth_service)
        self._workflows = WorkflowsClient(oauth_service)

    async def __aenter__(self):
        # Enter all specialized clients
        await self._contacts.__aenter__()
        await self._conversations.__aenter__()
        await self._opportunities.__aenter__()
        await self._calendars.__aenter__()
        await self._forms.__aenter__()
        await self._custom_fields.__aenter__()
        await self._notes_tasks.__aenter__()
        await self._users.__aenter__()
        await self._workflows.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Exit all specialized clients
        await self._contacts.__aexit__(exc_type, exc_val, exc_tb)
        await self._conversations.__aexit__(exc_type, exc_val, exc_tb)
        await self._opportunities.__aexit__(exc_type, exc_val, exc_tb)
        await self._calendars.__aexit__(exc_type, exc_val, exc_tb)
        await self._forms.__aexit__(exc_type, exc_val, exc_tb)
        await self._custom_fields.__aexit__(exc_type, exc_val, exc_tb)
        await self._notes_tasks.__aexit__(exc_type, exc_val, exc_tb)
        await self._users.__aexit__(exc_type, exc_val, exc_tb)
        await self._workflows.__aexit__(exc_type, exc_val, exc_tb)

    # Location Methods (keeping these in main client for now)

    async def get_locations(self, limit: int = 100, skip: int = 0) -> Dict[str, Any]:
        """Get all locations"""
        # Use the first available client for the request
        response = await self._contacts._request(
            "GET", "/locations/search", params={"limit": limit, "skip": skip}
        )
        return response.json()

    async def get_location(self, location_id: str) -> Dict[str, Any]:
        """Get a specific location"""
        response = await self._contacts._request("GET", f"/locations/{location_id}")
        return response.json()

    # Contact Methods - Delegate to ContactsClient

    async def get_contacts(
        self,
        location_id: str,
        limit: int = 100,
        skip: int = 0,
        query: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ContactList:
        """Get contacts for a location"""
        return await self._contacts.get_contacts(
            location_id=location_id,
            limit=limit,
            skip=skip,
            query=query,
            email=email,
            phone=phone,
            tags=tags,
        )

    async def get_contact(self, contact_id: str, location_id: str) -> Contact:
        """Get a specific contact"""
        return await self._contacts.get_contact(contact_id, location_id)

    async def create_contact(self, contact: ContactCreate) -> Contact:
        """Create a new contact"""
        return await self._contacts.create_contact(contact)

    async def update_contact(
        self, contact_id: str, updates: ContactUpdate, location_id: str
    ) -> Contact:
        """Update an existing contact"""
        return await self._contacts.update_contact(contact_id, updates, location_id)

    async def delete_contact(self, contact_id: str, location_id: str) -> bool:
        """Delete a contact"""
        return await self._contacts.delete_contact(contact_id, location_id)

    async def add_contact_tags(
        self, contact_id: str, tags: List[str], location_id: str
    ) -> Contact:
        """Add tags to a contact"""
        return await self._contacts.add_contact_tags(contact_id, tags, location_id)

    async def remove_contact_tags(
        self, contact_id: str, tags: List[str], location_id: str
    ) -> Contact:
        """Remove tags from a contact"""
        return await self._contacts.remove_contact_tags(contact_id, tags, location_id)

    # Conversation Methods - Delegate to ConversationsClient

    async def get_conversations(
        self,
        location_id: str,
        limit: int = 100,
        skip: int = 0,
        contact_id: Optional[str] = None,
        starred: Optional[bool] = None,
        unread_only: Optional[bool] = None,
    ) -> ConversationList:
        """Get conversations for a location"""
        return await self._conversations.get_conversations(
            location_id=location_id,
            limit=limit,
            skip=skip,
            contact_id=contact_id,
            starred=starred,
            unread_only=unread_only,
        )

    async def get_conversation(
        self, conversation_id: str, location_id: str
    ) -> Conversation:
        """Get a specific conversation"""
        return await self._conversations.get_conversation(conversation_id, location_id)

    async def create_conversation(
        self, conversation: ConversationCreate
    ) -> Conversation:
        """Create a new conversation"""
        return await self._conversations.create_conversation(conversation)

    async def get_messages(
        self, conversation_id: str, location_id: str, limit: int = 100, skip: int = 0
    ) -> MessageList:
        """Get messages for a conversation"""
        return await self._conversations.get_messages(
            conversation_id, location_id, limit, skip
        )

    async def send_message(
        self, conversation_id: str, message: MessageCreate, location_id: str
    ) -> Message:
        """Send a message in a conversation"""
        return await self._conversations.send_message(
            conversation_id, message, location_id
        )

    async def update_message_status(
        self, message_id: str, status: str, location_id: str
    ) -> Message:
        """Update the status of a message"""
        return await self._conversations.update_message_status(
            message_id, status, location_id
        )

    # Opportunity Methods - Delegate to OpportunitiesClient

    async def get_opportunities(
        self,
        location_id: str,
        limit: int = 100,
        skip: int = 0,
        filters: Optional[OpportunitySearchFilters] = None,
    ) -> OpportunitySearchResult:
        """Get opportunities for a location"""
        return await self._opportunities.get_opportunities(
            location_id=location_id, limit=limit, skip=skip, filters=filters
        )

    async def get_opportunity(
        self, opportunity_id: str, location_id: str
    ) -> Opportunity:
        """Get a specific opportunity"""
        return await self._opportunities.get_opportunity(opportunity_id, location_id)

    async def create_opportunity(self, opportunity: OpportunityCreate) -> Opportunity:
        """Create a new opportunity"""
        return await self._opportunities.create_opportunity(opportunity)

    async def update_opportunity(
        self, opportunity_id: str, updates: OpportunityUpdate, location_id: str
    ) -> Opportunity:
        """Update an existing opportunity"""
        return await self._opportunities.update_opportunity(
            opportunity_id, updates, location_id
        )

    async def delete_opportunity(self, opportunity_id: str, location_id: str) -> bool:
        """Delete an opportunity"""
        return await self._opportunities.delete_opportunity(opportunity_id, location_id)

    async def update_opportunity_status(
        self, opportunity_id: str, status: str, location_id: str
    ) -> Opportunity:
        """Update opportunity status"""
        return await self._opportunities.update_opportunity_status(
            opportunity_id, status, location_id
        )

    async def get_pipelines(self, location_id: str) -> List[Pipeline]:
        """Get all pipelines for a location

        NOTE: This is the only pipeline endpoint that exists in the API.
        Individual pipeline and stage endpoints do not exist.
        """
        return await self._opportunities.get_pipelines(location_id)

    # Calendar Methods - Delegate to CalendarsClient

    async def get_appointments(
        self,
        contact_id: str,
        location_id: str,
    ) -> AppointmentList:
        """Get appointments for a contact"""
        return await self._calendars.get_appointments(
            contact_id=contact_id,
            location_id=location_id,
        )

    async def get_appointment(
        self, appointment_id: str, location_id: str
    ) -> Appointment:
        """Get a specific appointment"""
        return await self._calendars.get_appointment(appointment_id, location_id)

    async def create_appointment(self, appointment: AppointmentCreate) -> Appointment:
        """Create a new appointment"""
        return await self._calendars.create_appointment(appointment)

    async def update_appointment(
        self, appointment_id: str, updates: AppointmentUpdate, location_id: str
    ) -> Appointment:
        """Update an existing appointment"""
        return await self._calendars.update_appointment(
            appointment_id, updates, location_id
        )

    async def delete_appointment(self, appointment_id: str, location_id: str) -> bool:
        """Delete an appointment"""
        return await self._calendars.delete_appointment(appointment_id, location_id)

    async def get_calendars(self, location_id: str) -> CalendarList:
        """Get all calendars for a location"""
        return await self._calendars.get_calendars(location_id)

    async def get_calendar(self, calendar_id: str, location_id: str) -> Calendar:
        """Get a specific calendar"""
        return await self._calendars.get_calendar(calendar_id, location_id)

    async def get_free_slots(
        self,
        calendar_id: str,
        location_id: str,
        start_date: date,
        end_date: Optional[date] = None,
        timezone: Optional[str] = None,
    ) -> FreeSlotsResult:
        """Get available time slots for a calendar"""
        return await self._calendars.get_free_slots(
            calendar_id, location_id, start_date, end_date, timezone
        )

    # Form Methods - Delegate to FormsClient

    async def get_forms(
        self, location_id: str, limit: int = 100, skip: int = 0
    ) -> FormList:
        """Get all forms for a location"""
        return await self._forms.get_forms(location_id, limit, skip)

    async def get_all_submissions(
        self,
        location_id: str,
        form_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> FormSubmissionList:
        """Get all form submissions for a location"""
        return await self._forms.get_all_submissions(
            location_id, form_id, contact_id, start_date, end_date, limit, skip
        )

    async def upload_form_file(
        self, file_upload: FormFileUploadRequest
    ) -> Dict[str, Any]:
        """Upload a file to a form's custom field"""
        return await self._forms.upload_form_file(file_upload)

    # Custom Field Methods - Delegate to CustomFieldsClient

    async def get_custom_fields(
        self, location_id: str, model: Optional[str] = None
    ) -> CustomFieldList:
        """Get all custom fields for a location"""
        return await self._custom_fields.get_custom_fields(location_id, model)

    async def get_custom_field(
        self, custom_field_id: str, location_id: str
    ) -> CustomField:
        """Get a specific custom field"""
        return await self._custom_fields.get_custom_field(custom_field_id, location_id)

    async def create_custom_field(
        self, location_id: str, field: CustomFieldCreate
    ) -> CustomField:
        """Create a new custom field"""
        return await self._custom_fields.create_custom_field(location_id, field)

    async def update_custom_field(
        self, custom_field_id: str, location_id: str, updates: CustomFieldUpdate
    ) -> CustomField:
        """Update an existing custom field"""
        return await self._custom_fields.update_custom_field(
            custom_field_id, location_id, updates
        )

    async def delete_custom_field(self, custom_field_id: str, location_id: str) -> bool:
        """Delete a custom field"""
        return await self._custom_fields.delete_custom_field(
            custom_field_id, location_id
        )

    # Custom Value Methods - Delegate to CustomFieldsClient

    async def get_custom_values(self, location_id: str) -> CustomValueList:
        """Get all custom values for a location"""
        return await self._custom_fields.get_custom_values(location_id)

    async def get_custom_value(
        self, custom_value_id: str, location_id: str
    ) -> CustomValue:
        """Get a specific custom value"""
        return await self._custom_fields.get_custom_value(custom_value_id, location_id)

    async def create_custom_value(
        self, location_id: str, value: CustomValueCreate
    ) -> CustomValue:
        """Create a new custom value"""
        return await self._custom_fields.create_custom_value(location_id, value)

    async def update_custom_value(
        self, custom_value_id: str, location_id: str, updates: CustomValueUpdate
    ) -> CustomValue:
        """Update an existing custom value"""
        return await self._custom_fields.update_custom_value(
            custom_value_id, location_id, updates
        )

    async def delete_custom_value(self, custom_value_id: str, location_id: str) -> bool:
        """Delete a custom value"""
        return await self._custom_fields.delete_custom_value(
            custom_value_id, location_id
        )

    # Note Methods - Delegate to NotesTasksClient

    async def get_notes(self, contact_id: str, location_id: str) -> NoteList:
        """Get all notes for a contact"""
        return await self._notes_tasks.get_notes(contact_id, location_id)

    async def get_note(self, contact_id: str, note_id: str, location_id: str) -> Note:
        """Get a specific note"""
        return await self._notes_tasks.get_note(contact_id, note_id, location_id)

    async def create_note(
        self, contact_id: str, note: NoteCreate, location_id: str
    ) -> Note:
        """Create a note on a contact"""
        return await self._notes_tasks.create_note(contact_id, note, location_id)

    async def update_note(
        self, contact_id: str, note_id: str, updates: NoteUpdate, location_id: str
    ) -> Note:
        """Update a note on a contact"""
        return await self._notes_tasks.update_note(
            contact_id, note_id, updates, location_id
        )

    async def delete_note(
        self, contact_id: str, note_id: str, location_id: str
    ) -> bool:
        """Delete a note from a contact"""
        return await self._notes_tasks.delete_note(contact_id, note_id, location_id)

    # Task Methods - Delegate to NotesTasksClient

    async def get_tasks(self, contact_id: str, location_id: str) -> TaskList:
        """Get all tasks for a contact"""
        return await self._notes_tasks.get_tasks(contact_id, location_id)

    async def get_task(self, contact_id: str, task_id: str, location_id: str) -> Task:
        """Get a specific task"""
        return await self._notes_tasks.get_task(contact_id, task_id, location_id)

    async def create_task(
        self, contact_id: str, task: TaskCreate, location_id: str
    ) -> Task:
        """Create a task on a contact"""
        return await self._notes_tasks.create_task(contact_id, task, location_id)

    async def update_task(
        self, contact_id: str, task_id: str, updates: TaskUpdate, location_id: str
    ) -> Task:
        """Update a task on a contact"""
        return await self._notes_tasks.update_task(
            contact_id, task_id, updates, location_id
        )

    async def update_task_completed(
        self, contact_id: str, task_id: str, completed: bool, location_id: str
    ) -> Task:
        """Update a task's completed status"""
        return await self._notes_tasks.update_task_completed(
            contact_id, task_id, completed, location_id
        )

    async def delete_task(
        self, contact_id: str, task_id: str, location_id: str
    ) -> bool:
        """Delete a task from a contact"""
        return await self._notes_tasks.delete_task(contact_id, task_id, location_id)

    # User Methods - Delegate to UsersClient (agency-level)

    async def search_users(self, company_id: str, **kwargs) -> UserList:
        """Search users across an agency"""
        return await self._users.search_users(company_id, **kwargs)

    async def get_users_by_location(self, location_id: str) -> UserList:
        """Get all users assigned to a location"""
        return await self._users.get_users_by_location(location_id)

    async def get_user(self, user_id: str) -> User:
        """Get a specific user"""
        return await self._users.get_user(user_id)

    async def create_user(self, user: UserCreate) -> User:
        """Create a new user"""
        return await self._users.create_user(user)

    async def update_user(self, user_id: str, updates: UserUpdate) -> User:
        """Update an existing user"""
        return await self._users.update_user(user_id, updates)

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        return await self._users.delete_user(user_id)

    # Workflow Methods - Delegate to WorkflowsClient

    async def get_workflows(self, location_id: str) -> WorkflowList:
        """Get all workflows for a location"""
        return await self._workflows.get_workflows(location_id)

    async def add_contact_to_workflow(
        self,
        contact_id: str,
        workflow_id: str,
        location_id: str,
        event_start_time: Optional[str] = None,
    ) -> bool:
        """Add a contact to a workflow"""
        return await self._workflows.add_contact_to_workflow(
            contact_id, workflow_id, location_id, event_start_time
        )

    async def remove_contact_from_workflow(
        self, contact_id: str, workflow_id: str, location_id: str
    ) -> bool:
        """Remove a contact from a workflow"""
        return await self._workflows.remove_contact_from_workflow(
            contact_id, workflow_id, location_id
        )
