from aiogram.fsm.state import State, StatesGroup

class AddAccount(StatesGroup):
    waiting_session_name = State()
    waiting_api_id = State()
    waiting_api_hash = State()
    waiting_phone = State()
    waiting_code = State()
    waiting_password = State()
    deleting_account = State()

class AddTarget(StatesGroup):
    choosing_type = State()
    waiting_username = State()
    waiting_chat_id = State()

class DeleteTarget(StatesGroup):
    choosing_target = State()

class SendMessage(StatesGroup):
    choosing_targets = State()
    choosing_send_mode = State()
    waiting_interval = State()
    waiting_content_type = State()
    waiting_text = State()
    waiting_media = State()

class CreateDraft(StatesGroup):
    waiting_content_type = State()
    waiting_text = State()
    waiting_media = State()

class ConfigureDraft(StatesGroup):
    choosing_draft = State()
    choosing_action = State()
    selecting_targets = State()
    selecting_accounts = State()

class SendDraft(StatesGroup):
    choosing_draft = State()
    choosing_send_mode = State()  # Добавлено
    waiting_interval = State()    # Добавлено

class DeleteDraft(StatesGroup):
    choosing_draft = State()

class ScheduleMessage(StatesGroup):
    choosing_targets = State()
    choosing_source = State()
    choosing_draft = State()
    waiting_content_type = State()
    waiting_text = State()
    waiting_media = State()
    waiting_time = State()

class DeleteScheduled(StatesGroup):
    choosing_message = State()

class AssignAccount(StatesGroup):
    choosing_target = State()
    choosing_account = State()

class RemoveAssignment(StatesGroup):
    choosing_target = State()
    choosing_account = State()
