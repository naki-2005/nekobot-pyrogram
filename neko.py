import os
import time
import asyncio
import nest_asyncio
import threading
import logging
import random
from flask import Flask, send_from_directory, request, render_template_string
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from process_command import process_command
from command.help import handle_help_callback
from command.mailtools.send import mail_query
from command.db.db import save_user_data_to_db, load_user_config, subir_bot_config, descargar_bot_config
from cmd_list import lista_cmd
from data.stickers import saludos, STICKER_SALUDO, STICKER_DESCANSO, STICKER_REACTIVADO
from data.vars import (
    api_id, api_hash, bot_token, admin_users, users, temp_users,
    temp_chats, vip_users, ban_users, MAIN_ADMIN, CODEWORD,
    BOT_IS_PUBLIC, PROTECT_CONTENT, allowed_ids, allowed_users
)
from command.admintools import process_access_callback
from command.admintools import guardar_parametro, get_main_buttons, get_accesscmd_buttons
import sqlite3

from my_server_flask import run_flask
from start_bot import start_data, start_data_2
from process_query import process_query

# -------- Bot de Telegram --------
nest_asyncio.apply()
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

bot_is_sleeping = False
sleep_duration = 0
start_sleep_time = 0

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

async def process_access_command(message):
    user_id = message.from_user.id
    if len(message.command) > 1 and message.command[1] == CODEWORD:
        if user_id not in temp_users:
            temp_users.append(user_id)
            allowed_users.append(user_id)
            await message.reply("Acceso concedido.")
        else:
            await message.reply("Ya estás en la lista de acceso temporal.")
    else:
        await message.reply("Palabra secreta incorrecta.")

@app.on_message()
async def handle_message(client, message):
    await lista_cmd(app)
    global bot_is_sleeping, start_sleep_time, sleep_duration
    user_id = message.from_user.id if message.from_user else ""
    username = message.from_user.username if message.from_user else ""
    chat_id = message.chat.id if message.chat else ""

    try:
        lvl = load_user_config(user_id, "lvl")
        int_lvl = int(lvl) if lvl is not None and lvl.isdigit() else 0
    except Exception as e:
        await message.reply(f"Error al verificar nivel remoto: {e}")
        return

    if int_lvl == 0:
        return

    if not is_bot_public():
        if int_lvl < 2:
            print(f"Acceso a {user_id} rechazado, Bot Public = {is_bot_public}")
            return

    if is_bot_public():
        if lvl is None or (lvl not in ["1", "2", "3", "4", "5", "6"] and int_lvl < 2):
            try:
                save_user_data_to_db(user_id, "lvl", "1")
                await message.reply("Registrado como usuario público, disfrute del bot")
                int_lvl = 1
            except Exception as e:
                await message.reply(f"Error {e}")

    if message.text and message.text.startswith("/reactive") and int_lvl == 6:
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

    if message.text and message.text.startswith("/sleep") and int_lvl == 6:
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

    if message.text and message.text.startswith("/access") and message.chat.type == "private":
        await process_access_command(message)
        return

    active_cmd = os.getenv('ACTIVE_CMD', '').lower()
    admin_cmd = os.getenv('ADMIN_CMD', '').lower()
    await process_command(client, message, active_cmd, admin_cmd, user_id, username, chat_id, int_lvl)


@app.on_callback_query()
async def callback_handler(client, callback_query):
    await process_query(client, callback_query)
    
logging.basicConfig(level=logging.ERROR)
async def main():
    if os.environ.get("MAIN_BOT", "").lower() == "true":
        start_data()

    start_data_2()

    threading.Thread(target=run_flask, daemon=True).start()

    await app.start()
    print("Bot iniciado y servidor Flask corriendo en puerto 5000.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Detención forzada realizada")
