from general.text import ATTEMPT_TO_KILL
from keyboards.inline.buttons.common import BACK_BTN
from keyboards.inline.callback_factory.recognize_user import (
    UserActionIndexCbData,
)
from keyboards.inline.keypads.mailing import (
    send_selection_to_players_kb,
    kill_or_poison_kb,
)
from services.base import RouterHelper
from services.game.actions_at_night import (
    get_game_state_and_data,
    take_action_and_save_data,
    send_messages_to_group_and_user,
)
from utils.common import save_notification_message
from mafia.roles import Poisoner
from states.states import UserFsm


class PoisonerSaver(RouterHelper):
    async def poisoner_chose_to_kill(self):
        game_state, game_data = await get_game_state_and_data(
            tg_obj=self.callback,
            state=self.state,
            dispatcher=self.dispatcher,
        )
        poisoned = game_data["poisoned"]
        poisoned[1] = 1
        await send_messages_to_group_and_user(
            callback=self.callback,
            game_data=game_data,
            message_to_user="Ты решил всех убить!",
            message_to_group=False,
        )
        for user_id in poisoned[0]:
            save_notification_message(
                game_data=game_data,
                processed_user_id=user_id,
                message=ATTEMPT_TO_KILL,
                current_user_id=self.callback.from_user.id,
            )
        await game_state.set_data(game_data)

    async def poisoner_poisons(self):
        game_state, game_data = await get_game_state_and_data(
            tg_obj=self.callback,
            state=self.state,
            dispatcher=self.dispatcher,
        )
        poisoned = game_data["poisoned"]
        exclude = (poisoned[0] if poisoned else []) + [
            self.callback.from_user.id
        ]
        await self.state.set_state(UserFsm.POISONER_CHOSE_TO_KILL)
        await self.callback.message.edit_text(
            "Кого собираешься отравить?",
            reply_markup=send_selection_to_players_kb(
                players_ids=game_data["live_players_ids"],
                players=game_data["players"],
                extra_buttons=(BACK_BTN,),
                exclude=exclude,
            ),
        )

    async def poisoner_cancels_selection(self):
        _, game_data = await get_game_state_and_data(
            tg_obj=self.callback,
            state=self.state,
            dispatcher=self.dispatcher,
        )
        await self.state.set_state(UserFsm.POISONER_CHOOSES_ACTION)
        await self.callback.message.edit_text(
            text=Poisoner.mail_message,
            reply_markup=kill_or_poison_kb(game_data=game_data),
        )

    async def poisoner_chose_victim(
        self, callback_data: UserActionIndexCbData
    ):
        game_state, game_data, user_id = (
            await take_action_and_save_data(
                callback=self.callback,
                callback_data=callback_data,
                state=self.state,
                dispatcher=self.dispatcher,
            )
        )
        poisoned = game_data["poisoned"]
        if poisoned:
            poisoned[0].append(user_id)
        else:
            poisoned[:] = [[user_id], 0]
        await game_state.set_data(game_data)
