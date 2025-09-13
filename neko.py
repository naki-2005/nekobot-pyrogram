import os
import time
import asyncio
import threading
import logging
import random
import nest_asyncio
import sqlite3
import argparse
import sys

from flask import Flask, send_from_directory, request, render_template_string
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from process_command import process_command
from command.db.db import save_user_data_to_db, load_user_config
from cmd_list import lista_cmd
from data.stickers import STICKER_DESCANSO, STICKER_REACTIVADO
from my_server_flask import run_flask
from start_bot import start_data, start_data_2
from process_query import process_query

nest_asyncio.apply()
from arg_parser import get_args

args = get_args()

if args.bot_token:
    app = Client("my_bot", api_id=args.api_id, api_hash=args.api_hash, bot_token=args.bot_token, sleep_threshold=5, max_concurrent_transmissions=True)
    cmd_list_initialized = False  
else:
    app = Client("my_bot", api_id=args.api_id, api_hash=args.api_hash, session_string=args.session_string, sleep_threshold=5, max_concurrent_transmissions=True)
    cmd_list_initialized = True  

bot_is_sleeping = False
sleep_duration = 0
start_sleep_time = 0
flask_thread = None

def is_bot_public() -> bool:
    ruta_db = os.path.join(os.getcwd(), 'bot_cmd.db')
    if not os.path.exists(ruta_db):
        return False
    try:
        conn = sqlite3.connect(ruta_db)
        cursor = conn.cursor()
        cursor.execute('SELECT valor FROM parametros WHERE nombre = ?', ('public',))
        resultado = cursor.fetchone()
        conn.close()
        if not resultado:
            return False
        return int(resultado[0]) == 1
    except Exception as e:
        print(f"[!] Error al acceder a bot_cmd.db: {e}")
        return False

def format_time(seconds):
    years = seconds // (365 * 24 * 3600)
    days = (seconds % (365 * 24 * 3600)) // (24 * 3600)
    hours = (seconds % (24 * 3600)) // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    result = []
    if years: result.append(f"{years} año" if years == 1 else f"{years} años")
    if days: result.append(f"{days} día" if days == 1 else f"{days} días")
    if hours: result.append(f"{hours} hora" if hours == 1 else f"{hours} horas")
    if minutes: result.append(f"{minutes} minuto" if minutes == 1 else f"{minutes} minutos")
    if seconds: result.append(f"{seconds} segundo" if seconds == 1 else f"{seconds} segundos")
    return ", ".join(result)

def restart_flask():
    global flask_thread
    if flask_thread and flask_thread.is_alive():
        print("[INFO] Reiniciando servidor Flask...")
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
    else:
        print("[INFO] Iniciando servidor Flask...")
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

@app.on_message()
async def handle_message(client, message):
    global cmd_list_initialized, bot_is_sleeping, start_sleep_time, sleep_duration

    if not cmd_list_initialized and getattr(args, "bot_token", None):
        try:
            await lista_cmd(app)
            cmd_list_initialized = True
        except Exception as e:
            if "USER_BOT_REQUIRED" in str(e):
                cmd_list_initialized = True
            else:
                raise

    is_anonymous = message.sender_chat is not None and message.from_user is None
    user_id = message.from_user.id if message.from_user else None
    username = message.from_user.username if message.from_user else ""
    chat_id = message.chat.id if message.chat else ""

    raw_group_ids = getattr(args, "group_id", []) or []
    group_ids = list(map(int, raw_group_ids.split(","))) if isinstance(raw_group_ids, str) else raw_group_ids

    raw_black_words = getattr(args, "black_words", []) or []
    black_words = raw_black_words.split(",") if isinstance(raw_black_words, str) else raw_black_words

    raw_free_users = getattr(args, "free_users", []) or []
    free_users = list(map(int, raw_free_users.split(","))) if isinstance(raw_free_users, str) else raw_free_users

    if chat_id in group_ids and (message.text or message.caption):
        content = (message.text or "") + " " + (message.caption or "")
        if any(word.lower() in content.lower() for word in black_words):
            if user_id not in free_users:
                try:
                    await message.delete()
                    return
                except Exception:
                    pass

    try:
        lvl_user = load_user_config(user_id, "lvl") if user_id else None
        int_lvl_user = int(lvl_user) if lvl_user and lvl_user.isdigit() else 0
    except Exception:
        return

    if int_lvl_user < 2:
        try:
            lvl_group = load_user_config(chat_id, "lvl")
            int_lvl_group = int(lvl_group) if lvl_group and lvl_group.isdigit() else 0
        except Exception:
            return

        if int_lvl_group < 2:
            return

    if is_anonymous and not is_bot_public():
        return

    if not is_anonymous and not is_bot_public() and int_lvl_user < 2:
        return

    if not is_anonymous and is_bot_public():
        if lvl_user is None or (lvl_user not in ["1", "2", "3", "4", "5", "6"] and int_lvl_user < 2):
            try:
                save_user_data_to_db(user_id, "lvl", "1")
                await message.reply("Registrado como usuario público, disfrute del bot")
                int_lvl_user = 1
            except Exception:
                pass

    if message.text and message.text.startswith("/reactive") and int_lvl_user == 6:
        if bot_is_sleeping:
            bot_is_sleeping = False
            await app.send_sticker(chat_id, sticker=random.choice(STICKER_REACTIVADO))
            await message.reply("Ok, estoy de vuelta.")
        return

    if bot_is_sleeping and start_sleep_time:
        remaining = max(0, sleep_duration - int(time.time() - start_sleep_time))
        await app.send_sticker(chat_id, sticker=random.choice(STICKER_DESCANSO))
        await message.reply(f"Actualmente estoy descansando, no recibo comandos.\n\nRegresaré en {format_time(remaining)}")
        return

    if message.text and message.text.startswith("/sleep") and int_lvl_user == 6:
        try:
            sleep_duration = int(message.text.split(" ")[1])
            bot_is_sleeping = True
            start_sleep_time = time.time()
            await message.reply(f"Ok, voy a descansar {format_time(sleep_duration)}.")
            await asyncio.sleep(sleep_duration)
            bot_is_sleeping = False
            await app.send_sticker(chat_id, sticker=random.choice(STICKER_REACTIVADO))
            await message.reply("Ok, estoy de vuelta.")
        except ValueError:
            await message.reply("Por favor, proporciona un número válido en segundos.")
        return

    if message.text and message.text.startswith("/flaskreset") and int_lvl_user >= 5:
        restart_flask()
        await message.reply("Servidor Flask reiniciado.")
        return

    await process_command(client, message, user_id or chat_id, username, chat_id, int_lvl_user)

@app.on_callback_query()
async def callback_handler(client, callback_query):
    await process_query(client, callback_query)

logging.basicConfig(level=logging.ERROR)

async def main():
    global flask_thread
    if args.owner:
        start_data()
    start_data_2()
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    await app.start()
    print("Bot iniciado y servidor Flask corriendo en puerto 5000.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Detención forzada realizada")
