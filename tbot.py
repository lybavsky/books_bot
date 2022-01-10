import asyncio
import datetime
import os
import django
from asgiref.sync import sync_to_async

from books.settings import TG_ES_MAX_SIZE, TG_COUNT_PER_PAGE, TG_TOKEN, COVERS_ENABLED

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "books.settings")
django.setup()

from books_catalog.models import Book, TgUser, TgHistory

import math
import zipfile
from io import BytesIO

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ContentType, User
from elasticsearch.exceptions import NotFoundError

from es.es import ESClient

esclient = None

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


def get_result_message(str_req, curr_page=1):
    res = esclient.es.search(index=esclient.getElasticIndex(), size=TG_ES_MAX_SIZE, body={
        "query": {
            "query_string": {
                "query": " AND ".join(str_req.split(" "))
            }

        }
    }, request_timeout=60)

    full_results = res["hits"]["hits"]
    if len(full_results) == 0:
        return ("Ничего не найдено, переформулируйте запрос", None)

    pagecount = math.ceil(len(full_results) / TG_COUNT_PER_PAGE)

    if len(full_results) <= TG_COUNT_PER_PAGE:
        results = full_results
    else:
        if len(full_results) > TG_COUNT_PER_PAGE * int(curr_page):
            results = full_results[TG_COUNT_PER_PAGE * (int(curr_page) - 1):TG_COUNT_PER_PAGE * int(curr_page)]
        else:
            results = full_results[TG_COUNT_PER_PAGE * (int(curr_page) - 1):]

    outress = "Найдено " + str(len(full_results)) + ": \n\n"
    for outres_t in results:
        outres = outres_t["_source"]
        outress += "*" + outres["title"] + "*\n"
        outress += "Автор: "
        outress += (str(outres["last_name"]) + " ") if outres["last_name"] != None else ""
        outress += (str(outres["first_name"]) if outres["first_name"] != None else "")
        outress += "\n"
        outress += "Скачать книгу:" + "(/download" + outres_t["_id"] + ")\n"

    outress += "Страница " + str(curr_page) + "/" + str(pagecount) + "\n"

    if pagecount == 1:
        keyboard_markup = None
    else:
        keyboard_markup = types.InlineKeyboardMarkup()
        text_and_data = (
        )

        # 1 . 3 4 5 . 10
        if pagecount <= 7:
            for page in range(pagecount):
                npage = page + 1
                text_and_data = (
                    *text_and_data, (('*' if int(curr_page) == npage else '') + str(npage), str_req + "@" + str(npage))
                )
        else:
            if int(curr_page) <= 4:
                for page in range(6):
                    npage = page + 1
                    text_and_data = (
                        *text_and_data,
                        (('*' if int(curr_page) == npage else '') + str(npage), str_req + "@" + str(npage))
                    )
                text_and_data = (
                    *text_and_data,
                    (str(pagecount), str_req + "@" + str(pagecount))
                )
            elif int(curr_page) + 3 >= pagecount:
                text_and_data = (
                    *text_and_data,
                    (str(1), str_req + "@" + str(1))
                )
                for page in reversed(range(6)):
                    npage = pagecount - page
                    text_and_data = (
                        *text_and_data,
                        (('*' if int(curr_page) == npage else '') + str(npage), str_req + "@" + str(npage))
                    )
            else:
                text_and_data = (
                    *text_and_data,
                    (str(1), str_req + "@" + str(1))
                )

                for page in range(5):
                    npage = int(curr_page) - 2 + page
                    text_and_data = (
                        *text_and_data,
                        (('*' if int(curr_page) == npage else '') + str(npage), str_req + "@" + str(npage))
                    )

                text_and_data = (
                    *text_and_data,
                    (str(pagecount), str_req + "@" + str(pagecount))
                )

        row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in text_and_data)

        keyboard_markup.row(*row_btns)

    return (outress, keyboard_markup)


def get_or_create(user: User):
    try:
        return TgUser.objects.filter(userid=user.id).get()
    except TgUser.DoesNotExist:
        user = TgUser(userid=user.id, first_name=user.first_name, last_name=user.last_name, lang=user.language_code,
                      allowed=False)
        user.save()
        return user


def start_bot():
    global esclient
    esclient = ESClient.getInstance()

    bot = Bot(token=TG_TOKEN)

    dp = Dispatcher(bot)

    @dp.message_handler(commands="start")
    async def send_start(msg: types.Message):
        user=get_or_create(msg.from_user)
        if not user.allowed:
            res = "Привет. У тебя нет доступа этому боту.\nВозможно, стоит запросить доступ у @lybavsky или админа этого бота - а потом еще что-нибудь напиши"
        else:
            res = "Просто введи название или автора (или и то, и другое) и подожди"

        add_to_history(user,"/start")

        await msg.answer(res, parse_mode="Markdown")

    @dp.message_handler(regexp="^\/download")
    async def send_welcome(msg: types.Message):
        user=get_or_create(msg.from_user)
        if not user.allowed:
            res = "Привет. У тебя нет доступа этому боту.\nВозможно, стоит запросить доступ у @lybavsky или админа этого бота - а потом еще что-нибудь напиши"
            await msg.answer(res, parse_mode="Markdown")
            return

        add_to_history(user,msg.text)


        id = msg.text[9:]

        try:
            res: Book = await sync_to_async(Book.objects.select_related('author').get, thread_sensitive=True)(id=id)

            author_n = ((str(res.author.last_name) + " ") if res.author.last_name != None else "") + \
                       (str(res.author.first_name) if res.author.first_name != None else "")

            tgres = "*" + res.name + "*\n"
            tgres += "Автор: "
            tgres += author_n + "\n"

            for fb2file in res.fb2file_set.all():
                tgres += "----\n"
                tgres += "Язык: " + str(fb2file.lang) + "\n"
                tgres += "Описание: " + fb2file.description + "\n"

            await msg.answer(tgres, parse_mode="Markdown")

            for fb2file in res.fb2file_set.all():
                if COVERS_ENABLED and fb2file.cover_path != None and fb2file.cover_path != "":
                    fn = fb2file.cover_path

                    f_cover = open(fn, "rb")

                    try:
                        await bot.send_photo(msg.from_user.id, photo=f_cover, caption=res.name + ", " + author_n)
                    finally:
                        f_cover.close()

                if fb2file.archive_path != "":
                    zipf = zipfile.ZipFile(fb2file.path, "r")
                    bs = zipf.read(fb2file.archive_path)
                    f = BytesIO(bs)
                    await bot.send_document(msg.from_user.id, (str(fb2file.id) + ".fb2", f))
                    f.close()
                else:
                    f = open(fb2file.path, "rb")
                    await bot.send_document(msg.from_user.id, (str(fb2file.id) + ".fb2", f))
                    f.close()


        except NotFoundError as e:
            await msg.answer("Can not find book with id " + id)

    @dp.message_handler(content_types=ContentType.TEXT)
    async def send_welcome(msg: types.Message):
        user=get_or_create(msg.from_user)
        if not user.allowed:
            res = "Привет. У тебя нет доступа этому боту.\nВозможно, стоит запросить доступ у @lybavsky или админа этого бота - а потом еще что-нибудь напиши"
            await msg.answer(res, parse_mode="Markdown")
            return

        add_to_history(user, msg.text)

        r = get_result_message(msg.text, 1)
        outress = r[0]
        keyboard_markup = r[1]

        print("outres ", outress)
        print(keyboard_markup, keyboard_markup)
        await msg.answer(outress, parse_mode="Markdown", reply_markup=keyboard_markup)

    @dp.callback_query_handler()
    async def inline_kb_answer_callback_handler(query: types.CallbackQuery):
        answer_data = query.data
        sep_idx = answer_data.rfind("@")
        page = answer_data[sep_idx + 1:]
        req = answer_data[0:sep_idx]

        r = get_result_message(req, page)

        try:
            await bot.edit_message_text(r[0], query.from_user.id, query.message.message_id, parse_mode="Markdown",
                                        reply_markup=r[1])
        except:
            await query.answer("same page, stupid")

    executor.start_polling(dp, skip_updates=True)


def add_to_history(user: TgUser, text: str):
    msg = TgHistory(tguser_id=user.id, date=datetime.datetime.now(), text=text)
    msg.save()

# start_bot()
