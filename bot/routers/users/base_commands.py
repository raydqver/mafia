from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from keyboards.inline.callback_factory.help import RoleCbData
from keyboards.inline.cb.cb_text import (
    HELP_CB,
    HOW_TO_PLAY_CB,
    HOW_TO_SEE_STATISTICS_CB,
    HOW_TO_SET_UP_GAME_CB,
    HOW_TO_START_GAME_CB,
    VIEW_ROLES_CB,
    WHAT_ARE_BIDS_CB,
)
from services.users.base import BaseRouter
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name=__name__)


@router.message(CommandStart(), StateFilter(default_state))
async def greetings_to_user(
    message: Message, session_with_commit: AsyncSession
):
    base = BaseRouter(
        message=message,
        session=session_with_commit,
    )
    await base.greetings_to_user()


@router.message(Command("help"))
async def handle_help_by_command(message: Message):
    base = BaseRouter(message=message)
    await base.handle_help()


@router.callback_query(F.data == HELP_CB)
async def handle_help_by_callback(callback: CallbackQuery):
    base = BaseRouter(message=callback.message)
    await base.handle_help()


@router.callback_query(F.data == VIEW_ROLES_CB)
async def view_roles(callback: CallbackQuery):
    base = BaseRouter(callback=callback)
    await base.view_roles()


@router.callback_query(F.data == HOW_TO_START_GAME_CB)
async def how_to_start_game(callback: CallbackQuery):
    base = BaseRouter(callback=callback)
    await base.how_to_start_game()


@router.callback_query(F.data == WHAT_ARE_BIDS_CB)
async def what_are_bids(callback: CallbackQuery):
    base = BaseRouter(callback=callback)
    await base.what_are_bids()


@router.callback_query(F.data == HOW_TO_PLAY_CB)
async def how_to_play(callback: CallbackQuery):
    base = BaseRouter(callback=callback)
    await base.how_to_play()


@router.callback_query(F.data == HOW_TO_SET_UP_GAME_CB)
async def how_to_set_up_game(callback: CallbackQuery):
    base = BaseRouter(callback=callback)
    await base.how_to_set_up_game()


@router.callback_query(F.data == HOW_TO_SEE_STATISTICS_CB)
async def how_to_see_statistics(callback: CallbackQuery):
    base = BaseRouter(callback=callback)
    await base.how_to_see_statistics()


@router.callback_query(RoleCbData.filter())
async def get_details_about_role(
    callback: CallbackQuery, callback_data: RoleCbData
):
    base = BaseRouter(callback=callback)
    await base.get_details_about_role(callback_data=callback_data)
