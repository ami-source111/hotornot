import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.core.config import settings
from src.bot.handlers import start, upload, browse, comments, dialog, report, block

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register routers (order matters for callback priority)
    dp.include_router(start.router)
    dp.include_router(upload.router)
    dp.include_router(browse.router)
    dp.include_router(comments.router)
    dp.include_router(dialog.router)
    dp.include_router(report.router)
    dp.include_router(block.router)

    logger.info("Bot started polling")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
