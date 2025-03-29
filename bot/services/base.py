from dataclasses import dataclass

from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, PollAnswer, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao.prohibited_roles import ProhibitedRolesDAO
from database.schemas.roles import UserTgId
from utils.pretty_text import make_build


@dataclass
class RouterHelper:
    callback: CallbackQuery | None = None
    state: FSMContext | None = None
    session: AsyncSession | None = None
    message: Message | None = None
    dispatcher: Dispatcher | None = None
    scheduler: AsyncIOScheduler | None = None
    broker: RabbitBroker | None = None
    REQUIRE_TO_SAVE: str = make_build(
        "❗️Чтобы сохранить изменения, нажмите «Сохранить💾»\n\n"
    )

    def _get_user_id(self):
        obj = self.callback or self.message
        return obj.from_user.id

    def _get_bot(self):
        obj = self.callback or self.message
        return obj.bot

    async def _get_banned_roles(self):
        user_id = self._get_user_id()
        dao = ProhibitedRolesDAO(session=self.session)
        result = await dao.find_all(UserTgId(user_tg_id=user_id))
        return [record.role for record in result]
