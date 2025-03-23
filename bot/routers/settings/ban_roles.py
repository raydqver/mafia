from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import or_f, and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from general.collection_of_roles import get_data_with_roles
from keyboards.inline.cb.cb_text import (
    VIEW_BANNED_ROLES_CB,
    SAVE_CB,
    EDIT_SETTINGS_CB,
    CLEAR_SETTINGS_CB,
    CANCEL_CB,
    BAN_EVERYTHING_CB,
)
from middlewares.db import (
    DatabaseMiddlewareWithCommit,
    DatabaseMiddlewareWithoutCommit,
)
from services.settings.ban_roles import RoleAttendant
from states.settings import SettingsFsm

router = Router(name=__name__)
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)
router.message.middleware(DatabaseMiddlewareWithCommit())
router.callback_query.middleware(DatabaseMiddlewareWithCommit())
router.callback_query.middleware(DatabaseMiddlewareWithoutCommit())
router.poll_answer.middleware(DatabaseMiddlewareWithCommit())


@router.callback_query(
    or_f(
        F.data == VIEW_BANNED_ROLES_CB,
        and_f(SettingsFsm.BAN_ROLES, F.data == CANCEL_CB),
    )
)
async def view_banned_roles(
    callback: CallbackQuery,
    state: FSMContext,
    session_without_commit: AsyncSession,
):
    attendant = RoleAttendant(
        callback=callback,
        state=state,
        session=session_without_commit,
    )
    await attendant.view_banned_roles()


@router.callback_query(
    SettingsFsm.BAN_ROLES, F.data == CLEAR_SETTINGS_CB
)
async def clear_banned_roles(
    callback: CallbackQuery,
    state: FSMContext,
    session_with_commit: AsyncSession,
):
    attendant = RoleAttendant(
        callback=callback, state=state, session=session_with_commit
    )
    await attendant.clear_banned_roles()


@router.callback_query(
    SettingsFsm.BAN_ROLES, F.data == BAN_EVERYTHING_CB
)
async def ban_everything(
    callback: CallbackQuery,
    state: FSMContext,
    session_with_commit: AsyncSession,
):
    attendant = RoleAttendant(
        callback=callback, state=state, session=session_with_commit
    )
    await attendant.ban_everything()


@router.callback_query(
    SettingsFsm.BAN_ROLES, F.data == EDIT_SETTINGS_CB
)
async def suggest_roles_to_ban(
    callback: CallbackQuery,
    state: FSMContext,
):
    attendant = RoleAttendant(callback=callback, state=state)
    await attendant.suggest_roles_to_ban()


@router.callback_query(
    SettingsFsm.BAN_ROLES, F.data.in_(get_data_with_roles().keys())
)
async def process_banned_roles(
    callback: CallbackQuery,
    state: FSMContext,
):
    attendant = RoleAttendant(
        callback=callback,
        state=state,
    )
    await attendant.process_banned_roles()


@router.callback_query(SettingsFsm.BAN_ROLES, F.data == SAVE_CB)
async def save_prohibited_roles(
    callback: CallbackQuery,
    state: FSMContext,
    session_with_commit: AsyncSession,
):
    attendant = RoleAttendant(
        callback=callback, state=state, session=session_with_commit
    )
    await attendant.save_prohibited_roles()
