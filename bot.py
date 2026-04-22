import sys
import glob
import importlib
from pathlib import Path
import logging
import asyncio
import os

from pyrogram import idle, __version__
from pyrogram.raw.all import layer
from pyrogram.errors import FloodWait

from database.ia_filterdb import Media
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script

from datetime import date, datetime
import pytz
from aiohttp import web
from plugins import web_server

from Jisshu.bot import JisshuBot
from Jisshu.util.keepalive import ping_server
from Jisshu.bot.clients import initialize_clients

# ✅ SAFE LOGGING (no crash if file missing)
try:
    logging.config.fileConfig('logging.conf')
except:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

ppath = "plugins/*.py"
files = glob.glob(ppath)

loop = asyncio.get_event_loop()


async def Jisshu_start():
    print('\nInitializing The Movie Provider Bot\n')

    # ✅ SAFE START (FloodWait handled)
    try:
        await JisshuBot.start()
    except FloodWait as e:
        print(f"Flood wait: {e.value} seconds")
        await asyncio.sleep(e.value)
        await JisshuBot.start()

    bot_info = await JisshuBot.get_me()
    JisshuBot.username = bot_info.username

    await initialize_clients()

    # ✅ Load plugins
    for name in files:
        patt = Path(name)
        plugin_name = patt.stem
        plugins_dir = Path(f"plugins/{plugin_name}.py")
        import_path = f"plugins.{plugin_name}"

        spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
        load = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(load)
        sys.modules[import_path] = load

        print(f"Imported => {plugin_name}")

    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # ✅ Database setup
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    await Media.ensure_indexes()

    me = await JisshuBot.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name

    JisshuBot.username = '@' + me.username

    logging.info(f"{me.first_name} started on @{me.username}")
    logging.info(script.LOGO)

    # ✅ Time log
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    today = date.today()

    await JisshuBot.send_message(
        chat_id=LOG_CHANNEL,
        text=script.RESTART_TXT.format(today, now.strftime("%H:%M:%S %p"))
    )

    # ✅ Web server (for deployment health check)
    app = web.AppRunner(await web_server())
    await app.setup()

    PORT = int(os.environ.get("PORT", 8000))
    await web.TCPSite(app, "0.0.0.0", PORT).start()

    print(f"Bot running on port {PORT}")

    await idle()


if __name__ == '__main__':
    try:
        loop.run_until_complete(Jisshu_start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')
