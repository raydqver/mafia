import asyncio
from random import shuffle

from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from cache.cache_types import (
    GameCache,
    Role,
    Roles,
    AliasesRole,
)
from general.exceptions import GameIsOver
from general.players import Groupings
from keyboards.inline.keypads.to_bot import get_to_bot_kb
from services.mailing import MailerToPlayers
from services.processing import (
    Executor,
)
from states.states import GameFsm
from utils.utils import (
    get_profiles,
    get_state_and_assign,
    make_pretty,
)


class Game:
    def __init__(
        self,
        message: Message,
        state: FSMContext,
        dispatcher: Dispatcher,
        scheduler: AsyncIOScheduler,
    ):

        self.message = message
        self.state = state
        self.dispatcher = dispatcher
        self.scheduler = scheduler
        self.bot = message.bot
        self.group_chat_id = self.message.chat.id
        self.mailer = MailerToPlayers(
            state=self.state,
            bot=self.bot,
            dispatcher=self.dispatcher,
            group_chat_id=self.group_chat_id,
        )
        self.executor = Executor(
            message=message,
            state=state,
            dispatcher=dispatcher,
            scheduler=scheduler,
            mailer=self.mailer,
        )

    async def start_game(
        self,
    ):

        await self.message.delete()

        await self.state.set_state(GameFsm.STARTED)
        await self.select_roles()
        await self.mailer.familiarize_players()
        await self.message.answer(
            text="Игра начинается!",
            reply_markup=get_to_bot_kb(),
        )
        while True:
            try:
                await self.start_night()
            except GameIsOver as e:
                await self.give_out_rewards(e=e)
                return

    async def start_night(
        self,
    ):
        game_data: GameCache = await self.state.get_data()
        game_data["number_of_night"] += 1
        profiles = get_profiles(
            live_players_ids=game_data["players_ids"],
            players=game_data["players"],
        )
        await self.state.set_data(game_data)
        await self.message.answer_photo(
            photo="https://i.pinimg.com/originals/f0/43/ed/f043edcac9690fdec845925508006459.jpg",
            caption=f"Наступает ночь {game_data['number_of_night']}.\n\nЖивые участники:{profiles}",
            reply_markup=get_to_bot_kb("Действовать!"),
        )
        await self.mailer.mailing()
        game_data["angels_died"].clear()
        await asyncio.sleep(35)
        await self.executor.delete_messages_from_to_delete(
            to_delete=game_data["to_delete"]
        )
        await self.executor.cancel_action()
        await self.mailer.send_promised_information_to_users()
        await self.executor.sum_up_after_night()
        await asyncio.sleep(4)
        await self.mailer.suggest_vote()
        await asyncio.sleep(4)
        await self.executor.delete_messages_from_to_delete(
            to_delete=game_data["to_delete"]
        )
        result = await self.executor.confirm_final_aim()
        if result:
            await asyncio.sleep(15)
        await self.executor.delete_messages_from_to_delete(
            to_delete=game_data["to_delete"]
        )
        await self.executor.sum_up_after_voting()
        await asyncio.sleep(2)
        await self.executor.clear_data_after_all_actions()

    async def give_out_rewards(self, e: GameIsOver):
        game_data: GameCache = await self.state.get_data()
        result = ""
        if e.winner is Groupings.criminals:
            result = "Игра завершена! Местная мафия подчинила город себе!\n"
        elif e.winner is Groupings.civilians:
            result = "Игра завершена! Вся преступная верхушка обезглавлена, город может спать спокойно!\n"
        winners = "\nПобедители:\n"
        losers = "\nПроигравшие:\n"
        winners_ids = set()
        for user_id, player in game_data["players"].items():
            text = f'{player["url"]} - {player["initial_role"]}\n'
            if int(user_id) in game_data["winners"]:
                winners += text
                winners_ids.add(user_id)
            elif int(user_id) in game_data["losers"]:
                losers += text
            elif e.winner == Groupings.criminals:
                if (
                    player["role"] == Roles.don.value.role
                    or AliasesRole.mafia.value.role
                ):
                    winners += text
                    winners_ids.add(user_id)
                else:
                    losers += text
            else:
                if player["role"] != Roles.don.value.role:
                    winners_ids.add(user_id)
                    winners += text
                else:
                    losers += text
        await self.bot.send_message(
            chat_id=self.group_chat_id,
            text=result + winners + losers,
        )
        await self.executor.delete_messages_from_to_delete(
            to_delete=game_data["to_delete"]
        )
        await asyncio.gather(
            *(
                self.reset_state(
                    chat_id=int(user_id),
                    is_win=user_id in winners_ids,
                    role=player["pretty_role"],
                )
                for user_id, player in game_data["players"].items()
            )
        )
        await self.state.clear()
        return

    async def reset_state(
        self,
        chat_id: int,
        is_win: bool,
        role: str,
    ):
        if is_win:
            text = f"Поздравлю! Ты победил в роли {role}"
        else:
            text = f"К несчастью, ты проиграл в роли {role}"
        await self.bot.send_message(chat_id=chat_id, text=text)
        state = await get_state_and_assign(
            dispatcher=self.dispatcher,
            chat_id=chat_id,
            bot_id=self.bot.id,
        )
        await state.clear()

    async def select_roles(self):
        game_data: GameCache = await self.state.get_data()
        ids = game_data["players_ids"][:]
        shuffle(ids)
        roles_tpl = tuple(Roles)
        roles = (
            roles_tpl[:3]
            + (AliasesRole.mafia,)
            + (AliasesRole.mafia,)
            + roles_tpl[3:]
        )
        for user_id, role in zip(ids, roles):
            current_role: Role = role.value
            roles = game_data[current_role.roles_key]
            game_data["players"][str(user_id)][
                "role"
            ] = current_role.role
            game_data["players"][str(user_id)]["pretty_role"] = (
                make_pretty(current_role.role)
            )
            game_data["players"][str(user_id)]["initial_role"] = (
                make_pretty(current_role.role)
            )
            game_data["players"][str(user_id)]["initial_role"] = (
                make_pretty(current_role.role)
            )
            game_data["players"][str(user_id)][
                "enum_name"
            ] = role.name
            game_data["players"][str(user_id)][
                "roles_key"
            ] = current_role.roles_key
            roles.append(user_id)
        await self.state.set_data(game_data)


# class Role(NamedTuple):
#     players: list[int]
#     role: str
