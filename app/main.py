import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from time import monotonic

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import GetUpdates
from aiogram.types import CallbackQuery, Message
from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.database import async_session_maker, engine
from app.handlers import base, projects
from app.health import setup_health_app

logger = logging.getLogger("nabd")


def make_dispatcher():
    dispatcher = Dispatcher()
    dispatcher.include_routers(base.router, projects.router)

    last_update: dict[int, float] = {}

    @dispatcher.update.outer_middleware()
    async def database_session(handler, event, data):
        user = data.get("event_from_user")
        if user and user.id in settings.admin_ids_list:
            now = monotonic()
            if now - last_update.get(user.id, float("-inf")) < 0.75:
                if event.callback_query:
                    await event.callback_query.answer("لحظة من فضلك…")
                return None
            last_update[user.id] = now
        async with async_session_maker() as session:
            return await handler(event, {**data, "session": session})

    @dispatcher.errors()
    async def report_error(event):
        logger.warning("Telegram update failed (%s)", type(event.exception).__name__)
        callback = event.update.callback_query
        message = event.update.message
        if isinstance(callback, CallbackQuery):
            with suppress(Exception):
                await callback.answer("تعذّر تنفيذ الطلب. حاول مجددًا.", show_alert=True)
        elif isinstance(message, Message):
            with suppress(Exception):
                await message.answer("تعذّر تنفيذ الطلب. حاول مجددًا.")
        return True

    return dispatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.bot_token or not settings.admin_ids_list:
        raise RuntimeError("BOT_TOKEN and at least one TELEGRAM_ADMIN_IDS entry are required")
    try:
        bot = Bot(
            token=settings.bot_token.get_secret_value(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    except ValueError:
        raise RuntimeError("Invalid BOT_TOKEN format") from None

    app.state.last_poll = float("-inf")

    @bot.session.middleware()
    async def track_polling(make_request, bot, method):
        is_poll = isinstance(method, GetUpdates)
        try:
            result = await make_request(bot, method)
        except TelegramNetworkError:
            if is_poll:
                app.state.last_poll = float("-inf")
            raise TelegramNetworkError(method, "Telegram connection failed") from None
        except Exception:
            if is_poll:
                app.state.last_poll = float("-inf")
            raise
        if is_poll:
            app.state.last_poll = monotonic()
        return result

    task = None
    try:
        try:
            async with asyncio.timeout(10), engine.connect() as connection:
                await connection.execute(text("SELECT id FROM projects LIMIT 0"))
                version = await connection.scalar(text("SELECT version_num FROM alembic_version"))
                if version != "0002_project_audit":
                    raise RuntimeError("Unexpected schema revision")
        except Exception:
            raise RuntimeError("Database unavailable or migrations missing") from None
        task = asyncio.create_task(
            dispatcher.start_polling(
                bot,
                handle_signals=False,
                close_bot_session=False,
                polling_timeout=10,
                tasks_concurrency_limit=8,
            ),
            name="nabd-telegram-polling",
        )
        app.state.polling_task = task
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as error:
                logger.warning("Telegram polling stopped (%s)", type(error).__name__)
        await bot.session.close()
        await engine.dispose()


dispatcher = make_dispatcher()
app = FastAPI(title="NABD Command Center API", lifespan=lifespan)
setup_health_app(app)


if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level)
    uvicorn.run(
        app, host="0.0.0.0", port=settings.port, workers=1, log_level=settings.log_level.lower()
    )
