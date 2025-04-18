import asyncio
from abc import ABC, abstractmethod
from contextlib import suppress
from random import shuffle
from typing import TYPE_CHECKING, Callable, Optional, Self

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import InlineKeyboardButton
from cache.cache_types import (
    GameCache,
    LastInteraction,
    PlayersIds,
    RolesLiteral,
    UserGameCache,
    UserIdInt,
)
from cache.extra import ExtraCache
from database.schemas.results import PersonalResultSchema
from general import settings
from general.groupings import Groupings
from general.text import MONEY_SYM, NUMBER_OF_NIGHT
from keyboards.inline.keypads.mailing import (
    send_selection_to_players_kb,
)
from mafia.roles.descriptions.description import RoleDescription
from utils.common import (
    get_criminals_ids,
    get_the_most_frequently_encountered_id,
)
from utils.informing import (
    get_profiles,
    remind_criminals_about_inspections,
    send_a_lot_of_messages_safely,
)
from utils.pretty_text import (
    make_build,
    make_pretty,
)
from utils.state import get_state_and_assign

if TYPE_CHECKING:
    from general.collection_of_roles import DataWithRoles


class RoleABC(ABC):
    dispatcher: Dispatcher
    bot: Bot
    state: FSMContext
    role: str
    role_id: RolesLiteral
    photo: str
    role_description: RoleDescription
    need_to_process: bool = False
    clearing_state_after_death: bool = True
    grouping: Groupings = Groupings.civilians
    there_may_be_several: bool = False
    purpose: str | Callable | None
    message_to_user_after_action: str | None = None
    message_to_group_after_action: str | None = None
    is_mass_mailing_list: bool = False
    extra_data: list[ExtraCache] | None = None
    state_for_waiting_for_action: State | None = None

    payment_for_treatment = 5
    payment_for_murder = 5
    payment_for_night_spent = 4

    is_alias: bool = False

    def __call__(
        self,
        dispatcher: Dispatcher,
        bot: Bot,
        state: FSMContext,
        all_roles: "DataWithRoles",
    ):
        self.all_roles = all_roles
        self.dispatcher = dispatcher
        self.bot = bot
        self.state = state
        self.temporary_roles = {}
        self.dropped_out: set[UserIdInt] = set()

    @property
    @abstractmethod
    def role_description(self) -> RoleDescription:
        pass

    def introducing_users_to_roles(self, game_data: GameCache):
        roles_tasks = []
        aliases_tasks = []
        other_tasks = []
        persons = game_data[self.roles_key]
        for number, user_id in enumerate(persons):
            photo = self.photo
            role_name = self.role
            purpose = self.purpose
            if number != 0 and self.alias:
                photo = self.alias.photo
                role_name = self.alias.role
                purpose = self.alias.purpose
            roles_tasks.append(
                self.bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=f"Твоя роль - "
                    f"{make_pretty(role_name)}! "
                    f"{purpose}",
                )
            )
            if len(game_data[self.roles_key]) > 1 and self.alias:
                profiles = get_profiles(
                    players_ids=persons,
                    players=game_data["players"],
                    role=True,
                )
                aliases_tasks.append(
                    self.bot.send_message(
                        chat_id=user_id,
                        text=make_build(
                            "❗️Твои союзники, с которыми можно общаться прямо в этом чате:\n"
                        )
                        + profiles,
                    )
                )
            if self.state_for_waiting_for_action:
                roles_tasks.append(
                    get_state_and_assign(
                        dispatcher=self.dispatcher,
                        chat_id=user_id,
                        bot_id=self.bot.id,
                        new_state=self.state_for_waiting_for_action,
                    )
                )
            if self.grouping == Groupings.criminals:
                teammates = [
                    user_id
                    for user_id in get_criminals_ids(game_data)
                    if user_id not in persons
                ]
                if teammates:
                    other_tasks.append(
                        self.bot.send_message(
                            chat_id=user_id,
                            text=make_build(
                                "❗️Сокомандники, с которыми можно общаться прямо в этом чате:\n"
                                + get_profiles(
                                    players_ids=teammates,
                                    players=game_data["players"],
                                    role=True,
                                )
                            ),
                        )
                    )
        return roles_tasks, aliases_tasks, other_tasks

    async def boss_is_dead(
        self,
        game_data: GameCache,
        current_id: int,
    ):
        url = game_data["players"][str(current_id)]["url"]
        role = game_data["players"][str(current_id)]["pretty_role"]
        role_id = game_data["players"][str(current_id)]["role_id"]
        players = game_data[self.roles_key]
        if not players:
            return
        shuffle(players)
        new_boss_id = players[0]
        new_boss_url = game_data["players"][str(new_boss_id)]["url"]
        game_data["players"][str(new_boss_id)]["pretty_role"] = (
            make_pretty(self.role)
        )
        game_data["players"][str(new_boss_id)]["role_id"] = role_id
        profiles = get_profiles(
            players_ids=game_data[self.roles_key],
            players=game_data["players"],
            role=True,
        )
        await send_a_lot_of_messages_safely(
            bot=self.bot,
            users=players,
            text=f"❗️❗️❗️Погиб {role} {url}.\n\n"
            f"Новый {role} - {new_boss_url}\n\n"
            f"Текущие союзники:\n{profiles}",
        )

    @classmethod
    @property
    def alias(cls) -> Optional["RoleABC"]:
        subclasses = cls.__subclasses__()
        if not subclasses:
            return None
        return subclasses[0]()

    @classmethod
    @property
    def roles_key(cls):
        return cls.__name__.lower() + "s"

    @classmethod
    @property
    def processed_users_key(cls):
        if cls.need_to_process:
            return f"processed_by_{cls.__name__.lower()}"

    @classmethod
    @property
    def last_interactive_key(cls):
        if (
            issubclass(cls, ActiveRoleAtNightABC)
            and cls.need_to_monitor_interaction
        ):
            return f"{cls.__name__}_history"

    @classmethod
    @property
    def processed_by_boss(cls):
        if cls.alias and cls.alias.is_mass_mailing_list:
            return f"processed_boss_{cls.__name__}"

    def get_money_for_victory_and_nights(
        self,
        game_data: GameCache,
        winning_group: Groupings,
        nights_lived: int,
        user_id: str,
    ):
        if winning_group != self.grouping:
            return 0, 0
        return self.grouping.value.payment * (
            len(game_data["players"])
            // settings.mafia.minimum_number_of_players
        ), (self.payment_for_night_spent * nights_lived)

    def earn_money_for_winning(
        self,
        winning_group: Groupings,
        game_data: GameCache,
        user_id: str,
        game_id: int,
    ) -> PersonalResultSchema:
        user_data = game_data["players"][user_id]
        count_of_nights = game_data["number_of_night"]
        nights_lived = user_data.get(
            "number_died_at_night", count_of_nights
        )
        nights_lived_text = f"⏳Дней и ночей прожито: {nights_lived} из {count_of_nights}"
        if int(user_id) in self.dropped_out:
            money_for_victory, money_for_nights = 0, 0
        else:
            money_for_victory, money_for_nights = (
                self.get_money_for_victory_and_nights(
                    game_data=game_data,
                    winning_group=winning_group,
                    nights_lived=nights_lived,
                    user_id=user_id,
                )
            )
        if money_for_victory:
            user_data["money"] += (
                money_for_victory + money_for_nights
            )
            text = make_build(
                f"🔥🔥🔥Поздравляю! Ты победил в роли {user_data['initial_role']} ({money_for_victory}{MONEY_SYM})!\n\n"
                f"{nights_lived_text} ({money_for_nights}{MONEY_SYM})\n"
            )
            return PersonalResultSchema(
                user_tg_id=int(user_id),
                game_id=game_id,
                role_id=user_data["initial_role_id"],
                is_winner=True,
                nights_lived=nights_lived,
                money=user_data["money"],
                text=text,
            )
        else:
            user_data["money"] = 0
            text = make_build(
                f"🚫К сожалению, ты проиграл в роли {user_data['initial_role']} (0{MONEY_SYM})!\n\n"
                f"{nights_lived_text} (0{MONEY_SYM})\n"
            )
            return PersonalResultSchema(
                user_tg_id=int(user_id),
                game_id=game_id,
                role_id=user_data["initial_role_id"],
                is_winner=False,
                nights_lived=nights_lived,
                money=user_data["money"],
                text=text,
            )

    def get_money_for_voting(
        self,
        voted_role: Self,
    ):
        if self.grouping == Groupings.other:
            return 0
        elif self.grouping != voted_role.grouping:
            return voted_role.payment_for_murder // 2
        else:
            return 0

    def add_money_to_all_allies(
        self,
        game_data: GameCache,
        money: int,
        custom_message: str | None = None,
        beginning_message: str | None = None,
        user_url: str | None = None,
        processed_role: Optional["RoleABC"] = None,
        at_night: bool = True,
        additional_players: str | None = None,
    ):
        if self.temporary_roles:
            money = 0
        players = game_data[self.roles_key]
        if additional_players:
            players += game_data[additional_players]
        for player_id in players:
            game_data["players"][str(player_id)]["money"] += money
            if custom_message:
                message = custom_message
            else:
                message = f"{beginning_message} {user_url} ({make_pretty(processed_role.role)})"
            message += " - {money}" + MONEY_SYM
            if self.temporary_roles:
                message += " (🚫ОБМАНУТ ВО ВРЕМЯ ИГРЫ)"
            time_of_day = (
                "🌃Ночь" if at_night else "🌟Голосование дня"
            )
            game_data["players"][str(player_id)][
                "achievements"
            ].append(
                [
                    f'{time_of_day} {game_data["number_of_night"]}.\n{message}',
                    money,
                ]
            )
        self.temporary_roles.clear()

    def earn_money_for_voting(
        self,
        voted_role: Self,
        voted_user: UserGameCache,
        game_data: GameCache,
        user_id: int,
    ) -> None:
        user_data = game_data["players"][str(user_id)]
        number_of_day = game_data["number_of_night"]
        earned_money = self.get_money_for_voting(
            voted_role=voted_role
        )
        user_data["money"] += earned_money
        achievements = user_data["achievements"]
        message = (
            (
                f"🌟День {number_of_day}.\nПовешение {voted_user['url']} "
                f"({voted_user['pretty_role']}) - "
            )
            + "{money}"
            + MONEY_SYM
        )
        achievements.append([message, earned_money])

    def get_processed_user_id(self, game_data: GameCache):
        if self.processed_by_boss:
            processed_id = get_the_most_frequently_encountered_id(
                game_data[self.processed_users_key]
            )
            if processed_id is None:
                if not game_data[self.processed_users_key]:
                    return None
                if not game_data[self.processed_by_boss]:
                    return None
                return game_data[self.processed_by_boss][0]
            return processed_id
        if game_data.get(self.processed_users_key):
            return game_data[self.processed_users_key][0]
        return None

    async def report_death(
        self,
        game_data: GameCache,
        at_night: bool | None,
        user_id: int,
    ):
        if at_night is True:
            message = "😢🌃К сожалению, тебя убили! Отправь напоследок все, что думаешь!"
        elif at_night is False:
            message = (
                "😢🌟К несчастью, тебя линчевали на голосовании!"
            )
        else:
            message = (
                "😡Ты выбываешь из игры за неактивность! "
                "Ты проиграешь вне зависимости от былых заслуг и результатов команды."
            )
            self.dropped_out.add(user_id)
        await self.bot.send_message(
            chat_id=user_id, text=make_build(message)
        )


class AliasRoleABC(ABC):
    is_alias = True
    is_mass_mailing_list: bool = False
    there_may_be_several: bool = True

    async def alias_is_dead(
        self, current_id: int, game_data: GameCache
    ):
        url = game_data["players"][str(current_id)]["url"]
        role = game_data["players"][str(current_id)]["pretty_role"]
        profiles = get_profiles(
            players_ids=game_data[self.roles_key],
            players=game_data["players"],
            role=True,
        )
        text = (
            f"❗️Погиб {role} {url}.\n\nТекущие союзники:\n{profiles}"
        )
        await send_a_lot_of_messages_safely(
            bot=self.bot,
            users=game_data[self.roles_key],
            text=text,
        )

    @classmethod
    @property
    def roles_key(cls):
        super_classes = cls.__bases__
        return super_classes[1].roles_key

    @classmethod
    @property
    def processed_users_key(cls):
        super_classes = cls.__bases__
        return super_classes[1].processed_users_key

    @classmethod
    @property
    def last_interactive_key(cls):
        super_classes = cls.__bases__
        return super_classes[1].last_interactive_key

    @classmethod
    @property
    def boss_name(cls):
        super_classes = cls.__bases__
        return super_classes[1].role


class ActiveRoleAtNightABC(RoleABC):
    state_for_waiting_for_action: State
    was_deceived: bool
    need_to_process: bool = True
    mail_message: str
    need_to_monitor_interaction: bool = True
    is_self_selecting: bool = False
    do_not_choose_others: int = 1
    do_not_choose_self: int = 1
    payment_for_treatment = 10
    payment_for_murder = 10

    @classmethod
    @property
    def notification_message(cls) -> str:
        return f"С тобой этой ночью взаимодействовал {make_pretty(cls.role)}"

    def leave_notification_message(
        self,
        game_data: GameCache,
    ):
        if self.notification_message:
            processed_user_id = self.get_processed_user_id(game_data)
            if processed_user_id:
                game_data["messages_after_night"].append(
                    [processed_user_id, self.notification_message]
                )

    def cancel_actions(self, game_data: GameCache, user_id: int):
        suffers = (
            game_data["tracking"]
            .get(str(user_id), {})
            .get("sufferers", [])
        )[:]
        if not suffers:
            return False
        for suffer in suffers:
            if (
                self.processed_users_key
                and suffer in game_data[self.processed_users_key]
            ):
                game_data[self.processed_users_key].remove(suffer)
            with suppress(KeyError, ValueError):
                game_data["tracking"][str(suffer)][
                    "interacting"
                ].remove(user_id)
            with suppress(KeyError, ValueError):
                game_data["tracking"][str(user_id)][
                    "sufferers"
                ].remove(suffer)

        if (
            self.processed_by_boss
            and user_id == game_data[self.roles_key][0]
        ):
            game_data[self.processed_by_boss].clear()

        if self.last_interactive_key:
            data: LastInteraction = game_data[
                self.last_interactive_key
            ]
            if self.is_alias is False:
                for suffer in suffers:
                    suffer_interaction = data[str(suffer)]
                    suffer_interaction.pop()
        return True

    async def send_survey(
        self,
        player_id: int,
        game_data: GameCache,
    ):

        markup = self.generate_markup(
            player_id=player_id,
            game_data=game_data,
        )
        game_data["wait_for"].append(player_id)
        with suppress(TelegramBadRequest):
            sent_survey = await self.bot.send_message(
                chat_id=player_id,
                text=self.mail_message,
                reply_markup=markup,
            )
            await self.save_information_about_mail_and_change_state(
                game_data=game_data,
                player_id=player_id,
                message_id=sent_survey.message_id,
            )

    async def save_information_about_mail_and_change_state(
        self,
        game_data: GameCache,
        player_id: int,
        message_id: int,
    ):
        game_data["to_delete"].append([player_id, message_id])
        await get_state_and_assign(
            dispatcher=self.dispatcher,
            chat_id=player_id,
            bot_id=self.bot.id,
            new_state=self.state_for_waiting_for_action,
        )

    async def send_survey_to_aliases(
        self,
        roles: PlayersIds,
        game_data: GameCache,
    ):
        tasks = []
        if self.alias and len(roles) > 1:
            for user_id in roles[1:]:
                if self.alias.is_mass_mailing_list:
                    tasks.append(
                        self.send_survey(
                            player_id=user_id,
                            game_data=game_data,
                        )
                    )
        await asyncio.gather(*tasks, return_exceptions=True)

    def generate_markup(
        self,
        player_id: int,
        game_data: GameCache,
        extra_buttons: tuple[InlineKeyboardButton, ...] = (),
    ):
        exclude = []
        current_number = game_data["number_of_night"]
        if self.is_self_selecting is False:
            exclude = [player_id]
        for processed_user_id, numbers in game_data.get(
            self.last_interactive_key, {}
        ).items():
            if not numbers:
                continue
            last_number_of_night = numbers[-1]
            if int(processed_user_id) == player_id:
                constraint = self.do_not_choose_self
            else:
                constraint = self.do_not_choose_others
            if constraint is None:
                exclude.append(int(processed_user_id))
            elif (
                current_number - last_number_of_night
                < constraint + 1
            ):
                exclude.append(int(processed_user_id))

        if game_data["live_players_ids"] == exclude:
            return
        return send_selection_to_players_kb(
            players_ids=game_data["live_players_ids"],
            players=game_data["players"],
            exclude=exclude,
            extra_buttons=extra_buttons,
        )

    def get_roles(self, game_data: GameCache):
        roles = game_data[self.roles_key]
        if not roles:
            return
        return roles

    def get_general_text_before_sending(
        self,
        game_data: GameCache,
    ) -> str | None:
        if self.grouping == Groupings.criminals:
            return remind_criminals_about_inspections(game_data)

    @staticmethod
    def allow_sending_mailing(game_data: GameCache) -> bool:
        return True

    async def mailing(self, game_data: GameCache):
        roles = self.get_roles(game_data)
        if not roles:
            return
        if self.allow_sending_mailing(game_data) is not True:
            text = (
                NUMBER_OF_NIGHT.format(game_data["number_of_night"])
                + "😜У тебя сегодня выходной!"
            )
            await send_a_lot_of_messages_safely(
                bot=self.bot,
                users=[roles[0]],
                text=make_build(text),
            )
            return
        general_text = self.get_general_text_before_sending(
            game_data
        )
        if general_text is not None:
            text = make_build(general_text)
            await send_a_lot_of_messages_safely(
                bot=self.bot,
                users=roles,
                text=text,
            )

        await self.send_survey(
            player_id=roles[0],
            game_data=game_data,
        )
        await self.send_survey_to_aliases(
            roles=roles,
            game_data=game_data,
        )
