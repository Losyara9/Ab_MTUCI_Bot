from aiogram.fsm.state import StatesGroup, State

class Registration(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_fullname = State()
    waiting_for_inn = State()

class Menu(StatesGroup):
    main = State()
    choose_info_type = State()
    change_inn = State()
    change_email = State()
    report_issue = State()