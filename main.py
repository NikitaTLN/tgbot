from __future__ import annotations

import asyncio
import logging

from bot import RaceNotifier
from client import OnlyDraftsClient, format_no_races_message
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def race_poller(od: OnlyDraftsClient, notifier: RaceNotifier, interval: int):
    logger.info("Race poller started (interval=%ds)", interval)
    first_run = True
    while True:
        try:
            races = await od.get_races()
            new_races = od.get_new_races(races)
            for race in new_races:
                logger.info("New race found: #%s — %s", race["id"], race.get("name"))
                await notifier.send_race_notification(race)
            if first_run and not races and notifier._chat_id is not None:
                logger.info("No races available, sending startup message")
                await notifier.bot.send_message(
                    chat_id=notifier._chat_id,
                    text=format_no_races_message(),
                )
            first_run = False
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Race poller error: %s", exc)
            await asyncio.sleep(5)
            continue
        await asyncio.sleep(interval)


async def main():
    cfg = Config()
    cfg.validate()

    od = OnlyDraftsClient(
        email=cfg.od_email,
        password=cfg.od_password,
        base_url=cfg.base_url,
    )
    await od.login()

    notifier = RaceNotifier(token=cfg.bot_token, chat_id=cfg.chat_id)

    logger.info("Starting... CHAT_ID=%s", cfg.chat_id or "NOT SET — send a message to the bot to get it")
    logger.info("Press Ctrl+C to stop")

    poller_task = asyncio.create_task(race_poller(od, notifier, cfg.poll_interval))
    try:
        await notifier.start_polling()
    finally:
        poller_task.cancel()
        await asyncio.gather(poller_task, return_exceptions=True)
        await od.close()
        await notifier.close()
        logger.info("Stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
