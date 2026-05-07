from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from client import format_race_message

logger = logging.getLogger(__name__)


class RaceNotifier:
    def __init__(self, token: str, chat_id: int | None = None):
        self.bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()
        self._chat_id = chat_id
        self._setup_handlers()

    def _setup_handlers(self):
        @self.dp.my_chat_member()
        async def on_my_chat_member(update: types.ChatMemberUpdated):
            chat = update.chat
            logger.info(
                "Bot added to chat: id=%s type=%s title=%s",
                chat.id, chat.type, chat.title,
            )

        @self.dp.message()
        async def on_message(msg: types.Message):
            chat = msg.chat
            logger.info(
                "Message from chat: id=%s type=%s title=%s",
                chat.id, chat.type, chat.title,
            )
            await msg.reply(
                f"This chat's ID is <code>{chat.id}</code>\n"
                f"Type: {chat.type}\n"
                f"Title: {chat.title or '—'}"
            )

        @self.dp.channel_post()
        async def on_channel_post(msg: types.Message):
            chat = msg.chat
            logger.info(
                "Channel post from chat: id=%s type=%s title=%s",
                chat.id, chat.type, chat.title,
            )
            await msg.reply(
                f"This channel's ID is <code>{chat.id}</code>\n"
                f"Title: {chat.title or '—'}"
            )

    async def send_race_notification(self, race: dict[str, Any]):
        if self._chat_id is None:
            logger.warning("CHAT_ID not set, cannot send notification")
            return
        text = format_race_message(race)
        try:
            await self.bot.send_message(chat_id=self._chat_id, text=text)
            logger.info("Sent notification for race #%s", race.get("id"))
        except Exception as exc:
            logger.error("Failed to send notification for race #%s: %s", race.get("id"), exc)

    async def start_polling(self):
        logger.info("Starting bot polling...")
        await self.dp.start_polling(self.bot)

    async def close(self):
        await self.bot.session.close()
