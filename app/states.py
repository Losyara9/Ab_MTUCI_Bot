from aiogram.fsm.state import StatesGroup, State

class Registration(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_code = State()

class Menu(StatesGroup):
    main = State()
    choose_info_type = State()
    change_inn = State()
    change_email = State()
    report_issue = State()
    waiting_for_email_code = State()