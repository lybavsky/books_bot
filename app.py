import asyncio
import logging
import os
import zipfile
from io import BytesIO
from multiprocessing import Process
from pathlib import Path


import uvicorn
from aiogram import Dispatcher, Bot, types
from aiogram.bot import bot
from aiogram.types import ContentType
from aiogram.utils import executor
from asgiref.sync import sync_to_async
from django.core.asgi import get_asgi_application
from elasticsearch.exceptions import NotFoundError

from books.settings import  TG_TOKEN, COVERS_ENABLED
from books_catalog.middleware import InjectMiddleware
from tbot import start_bot

BASE_DIR = Path(__file__).resolve()
#.parent

logging.basicConfig(level=logging.INFO)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "books.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

class MyServer:
    app = get_asgi_application()

    config = uvicorn.Config(app=app, loop=loop, port=8000, host="0.0.0.0")
    server = uvicorn.Server(config=config)

    @classmethod
    def run(cls):
        asyncio.run(cls.on_startup())
        asyncio.run(cls.server.serve())
        asyncio.run(cls.on_shutdown())

    @staticmethod
    async def on_startup() -> None:
        #InjectMiddleware.inject_params = dict(bot=MyBot.bot)
        pass

    @staticmethod
    async def on_shutdown() -> None:
        pass


class MyBot:
    bot = Bot(token=TG_TOKEN)
    dp = Dispatcher(bot)

    Bot.set_current(bot)
    Dispatcher.set_current(dp)


    @classmethod
    def run(cls):
        # executor.start_polling(
        #     cls.dp, on_startup=cls.on_startup, on_shutdown=cls.on_shutdown
        # )
        start_bot()

    @staticmethod
    async def on_startup(dp: Dispatcher):
        pass

    @staticmethod
    async def on_shutdown(dp: Dispatcher):
        pass



def run_app():
    bot = Process(target=MyBot.run)
    server = Process(target=MyServer.run)

    bot.start()
    server.start()


if __name__ == "__main__":
    run_app()
