from aiogram import Router, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from cache.cache_types import UserCache, GameCache
from keyboards.inline.callback_factory.user_index import (
    UserIndexCbData,
)
from services.registartion import get_state_and_assign
from states.states import UserFsm

router = Router()


@router.callback_query(
    UserFsm.MAFIA_ATTACKS, UserIndexCbData.filter()
)
async def mafia_attacks(
    callback: CallbackQuery,
    callback_data: UserIndexCbData,
    state: FSMContext,
    dispatcher: Dispatcher,
):
    user_data: UserCache = await state.get_data()
    game_state = await get_state_and_assign(
        dispatcher=dispatcher,
        chat_id=user_data["game_chat"],
        bot_id=callback.bot.id,
    )
    game_data: GameCache = await game_state.get_data()
    died_user_id = game_data["players_ids"][callback_data.user_index]
    game_data["died"].append(died_user_id)
    url = game_data["players"][str(died_user_id)]["url"]
    await callback.message.edit_text(f"Ты выбрал убить {url}")
    game_data["to_delete"].remove(callback.message.message_id)


@router.callback_query(
    UserFsm.DOCTOR_TREATS, UserIndexCbData.filter()
)
async def doctor_treats(
    callback: CallbackQuery,
    callback_data: UserIndexCbData,
    state: FSMContext,
    dispatcher: Dispatcher,
):
    user_data: UserCache = await state.get_data()
    game_state = await get_state_and_assign(
        dispatcher=dispatcher,
        chat_id=user_data["game_chat"],
        bot_id=callback.bot.id,
    )
    game_data: GameCache = await game_state.get_data()
    recovered_user_id = game_data["players_ids"][
        callback_data.user_index
    ]
    game_data["recovered"].append(recovered_user_id)
    url = game_data["players"][str(recovered_user_id)]["url"]
    await callback.message.edit_text(f"Ты выбрал вылечить {url}")
    game_data["to_delete"].remove(callback.message.message_id)


@router.callback_query(
    UserFsm.POLICEMAN_CHECKS, UserIndexCbData.filter()
)
async def policeman_checks(
    callback: CallbackQuery,
    callback_data: UserIndexCbData,
    state: FSMContext,
    dispatcher: Dispatcher,
):
    user_data: UserCache = await state.get_data()
    game_state = await get_state_and_assign(
        dispatcher=dispatcher,
        chat_id=user_data["game_chat"],
        bot_id=callback.bot.id,
    )
    game_data: GameCache = await game_state.get_data()

    checked_user_id = game_data["players_ids"][
        callback_data.user_index
    ]
    role = game_data["players"][str(checked_user_id)]["role"]
    url = game_data["players"][str(checked_user_id)]["url"]
    await callback.message.edit_text(f"{url} - {role}!")
    game_data["to_delete"].remove(callback.message.message_id)
