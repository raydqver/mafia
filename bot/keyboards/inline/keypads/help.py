from operator import attrgetter

from aiogram.types import InlineKeyboardButton

from general.collection_of_roles import get_data_with_roles
from general.text import ROLES_SELECTION, CONFIGURE_GAME_SECTION
from keyboards.inline.builder import generate_inline_kb
from keyboards.inline.buttons.common import (
    HELP_BTN,
    ADD_BOT_TO_GROUP,
)
from keyboards.inline.callback_factory.help import RoleCbData
from keyboards.inline.cb.cb_text import (
    VIEW_ROLES_CB,
    HOW_TO_START_GAME_CB,
    WHAT_ARE_BIDS_CB,
    HOW_TO_PLAY_CB,
    HOW_TO_SET_UP_GAME_CB,
    HOW_TO_SEE_STATISTICS_CB,
)


def get_roles_kb():
    all_roles = get_data_with_roles()
    buttons = [
        InlineKeyboardButton(
            text=role.role + role.grouping.value.name[-1],
            callback_data=RoleCbData(role_id=role_id).pack(),
        )
        for role_id, role in all_roles.items()
    ]
    buttons.sort(key=attrgetter("text"))
    buttons.append(HELP_BTN)
    return generate_inline_kb(
        data_with_buttons=buttons, leave_1_each=1
    )


def help_options_kb():
    buttons = [
        HOW_TO_START_GAME_BTN,
        InlineKeyboardButton(
            text="Что за ставки?🃏",
            callback_data=WHAT_ARE_BIDS_CB,
        ),
        InlineKeyboardButton(
            text="Как играть?🎮",
            callback_data=HOW_TO_PLAY_CB,
        ),
        HOW_TO_SET_UP_GAME_BTN,
        InlineKeyboardButton(
            text="Как посмотреть статистику?📈",
            callback_data=HOW_TO_SEE_STATISTICS_CB,
        ),
        ROLES_SELECTION_BTN,
        ADD_BOT_TO_GROUP,
    ]
    return generate_inline_kb(data_with_buttons=buttons)


def to_help_kb():
    return generate_inline_kb(
        data_with_buttons=[ADD_BOT_TO_GROUP, HELP_BTN]
    )


def go_back_to_options_kb():
    buttons = [
        InlineKeyboardButton(
            text="К ролям🎭", callback_data=VIEW_ROLES_CB
        ),
        HELP_BTN,
    ]
    return generate_inline_kb(data_with_buttons=buttons)


HOW_TO_START_GAME_BTN = InlineKeyboardButton(
    text="Как начать игру?🎲",
    callback_data=HOW_TO_START_GAME_CB,
)
ROLES_SELECTION_BTN = InlineKeyboardButton(
    text=ROLES_SELECTION, callback_data=VIEW_ROLES_CB
)
HOW_TO_SET_UP_GAME_BTN = InlineKeyboardButton(
    text=CONFIGURE_GAME_SECTION, callback_data=HOW_TO_SET_UP_GAME_CB
)
