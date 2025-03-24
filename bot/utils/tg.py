import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ChatMemberOwner,
    ChatMemberAdministrator,
)

from cache.cache_types import (
    ChatsAndMessagesIds,
    UserIdInt,
    GameCache,
)
from utils.utils import get_state_and_assign


async def delete_message(message: Message):
    with suppress(TelegramBadRequest, AttributeError):
        await message.delete()


async def delete_message_by_chat(
    bot: Bot, chat_id: int, message_id: int
):
    with suppress(TelegramBadRequest):
        await bot.delete_message(
            chat_id=chat_id, message_id=message_id
        )


async def reset_user_state(
    dispatcher: Dispatcher, user_id: int, bot_id: int
):
    state = await get_state_and_assign(
        dispatcher=dispatcher,
        chat_id=user_id,
        bot_id=bot_id,
    )
    await state.clear()


async def reset_state_to_all_users(
    dispatcher: Dispatcher, bot_id: int, users_ids: list[UserIdInt]
):
    await asyncio.gather(
        *(
            [
                reset_user_state(
                    dispatcher=dispatcher,
                    user_id=user_id,
                    bot_id=bot_id,
                )
                for user_id in users_ids
            ]
        )
    )


async def clear_game_data(
    game_data: GameCache,
    bot: Bot,
    dispatcher: Dispatcher,
    state: FSMContext,
    message_id: int,
):
    await bot.delete_message(
        chat_id=game_data["game_chat"], message_id=message_id
    )
    await delete_messages_from_to_delete(
        bot=bot,
        to_delete=game_data["to_delete"],
        state=None,
    )
    await reset_state_to_all_users(
        dispatcher=dispatcher,
        bot_id=bot.id,
        users_ids=game_data["players_ids"],
    )
    await state.clear(),


async def check_user_for_admin_rights(
    bot: Bot, chat_id: int, user_id: int
) -> bool:
    member = await bot.get_chat_member(
        chat_id=chat_id, user_id=user_id
    )
    return isinstance(
        member, (ChatMemberOwner, ChatMemberAdministrator)
    )


async def delete_messages_from_to_delete(
    bot: Bot,
    to_delete: ChatsAndMessagesIds,
    state: FSMContext | None,
):
    await asyncio.gather(
        *(
            delete_message_by_chat(
                bot=bot,
                chat_id=chat_id,
                message_id=message_id,
            )
            for chat_id, message_id in to_delete
        )
    )
    if state:
        await state.update_data({"to_delete": []})
