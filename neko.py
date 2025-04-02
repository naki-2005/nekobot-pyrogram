import os
import asyncio
import nest_asyncio
from pyrogram import Client, filters
from process_command import process_command
from command.htools import manejar_opcion
from command.help import handle_help_callback, handle_help
import time  # Importación necesaria
import threading  # Importación necesaria para hilos
from data.stickers import saludos
import random
from data.vars import api_id, api_hash, bot_token, admin_users, users, temp_users, temp_chats, vip_users, ban_users, MAIN_ADMIN, CODEWORD, BOT_IS_PUBLIC, PROTECT_CONTENT, allowed_ids, allowed_users
nest_asyncio.apply()

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Inicializar variables globales
bot_is_sleeping = False
sleep_duration = 0
start_sleep_time = 0  # Inicializada con 0 para evitar problemas

# Función para verificar si el bot es público
def is_bot_public():
    return BOT_IS_PUBLIC

# Función para mantener activa la sesión con animación dinámica
def mantener_sesion_activa():
    estados = ["Manteniendo la sesión activa.", 
               "Manteniendo la sesión activa..", 
               "Manteniendo la sesión activa..."]
    i = 0

    while True:
        print(f'\r{estados[i % len(estados)]}', end='', flush=True)
        i += 1
        time.sleep(3)  # Actualiza cada 3 segundos

# Crear un hilo separado para mantener la sesión activa
hilo = threading.Thread(target=mantener_sesion_activa, daemon=True)
hilo.start()

# Comando para procesar acceso temporal
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

# Manejador de mensajes
@app.on_message()
async def handle_message(client, message):
    global bot_is_sleeping, start_sleep_time, sleep_duration
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    auto = True

    # Validar si el usuario está baneado
    if user_id in ban_users:
        return

    # Validar si el bot no es público y el usuario no tiene acceso
    if not is_bot_public() and user_id not in allowed_users and chat_id not in allowed_users:
        return

    # Comando /reactive
    if message.text and message.text.startswith("/reactive") and (str(user_id) == MAIN_ADMIN or username.lower() == MAIN_ADMIN.lower()):
        if bot_is_sleeping:
            bot_is_sleeping = False

            # Notificar que el bot está activo nuevamente
            await client.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAIKa2fr9k_RUYKn3a2ESnotX5OZix-DAAJlOgAC4KOCB0AuzmaDZs-sHgQ"
            )
            time.sleep(3)
            await message.reply("Ok, estoy de vuelta.")
        return

    # Manejo del estado del bot cuando está en descanso
    if bot_is_sleeping and start_sleep_time:
        remaining_time = max(0, sleep_duration - int(time.time() - start_sleep_time))
        await client.send_sticker(
            chat_id=message.chat.id,
            sticker="CAACAgIAAxkBAAIKZWfr9RGuAW3W0j9az_LcQTeV8sXvAAIWSwAC4KOCB9L-syYc0ZfXHgQ"
        )
        time.sleep(3)
        await message.reply(f"Actualmente estoy descansando, no recibo comandos.\n\nRegresa en {remaining_time} segundos para reactivarse.")
        return

    if message.text and message.text.startswith("/sleep") and (str(user_id) == MAIN_ADMIN or username.lower() == MAIN_ADMIN.lower()):
        try:
            sleep_duration = int(message.text.split(" ")[1])
            bot_is_sleeping = True
            start_sleep_time = time.time()

            # Convertir segundos a años, días, horas, minutos y segundos
            years = sleep_duration // (365 * 24 * 3600)
            days = (sleep_duration % (365 * 24 * 3600)) // (24 * 3600)
            hours = (sleep_duration % (24 * 3600)) // 3600
            minutes = (sleep_duration % 3600) // 60
            seconds = sleep_duration % 60

            # Crear formato dinámico
            formatted_time_parts = []
            if years > 0:
                formatted_time_parts.append(f"{years} años")
            if days > 0:
                formatted_time_parts.append(f"{days} días")
            if hours > 0:
                formatted_time_parts.append(f"{hours} horas")
            if minutes > 0:
                formatted_time_parts.append(f"{minutes} minutos")
            if seconds > 0:
                formatted_time_parts.append(f"{seconds} segundos")

            formatted_time = ", ".join(formatted_time_parts)

            # Enviar sticker y mensaje
            await client.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAIKaGfr9YQxXzDbZD24aFoOoLvFUC9DAAIVSwAC4KOCB43TpRr21-13HgQ"
            )
            time.sleep(3)
            await message.reply(f"Ok, voy a descansar {formatted_time}.")

            # Temporizador para finalizar descanso
            await asyncio.sleep(sleep_duration)
            bot_is_sleeping = False

            # Notificar al MAIN_ADMIN que terminó el descanso
            await message.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAIKa2fr9k_RUYKn3a2ESnotX5OZix-DAAJlOgAC4KOCB0AuzmaDZs-sHgQ"
            )
            time.sleep(3)
            await message.reply("Ok, estoy de vuelta.")

        except ValueError:
            await message.reply("Por favor, proporciona un número válido en segundos.")
        return

    # Comando /access
    if message.text and message.text.startswith("/access") and message.chat.type == "private":
        await process_access_command(message)
        return

    # Procesar comandos activos
    active_cmd = os.getenv('ACTIVE_CMD', '').lower()
    admin_cmd = os.getenv('ADMIN_CMD', '').lower()
    await process_command(client, message, active_cmd, admin_cmd, user_id, username, chat_id)

async def notify_main_admin():
    if MAIN_ADMIN:
        try:
            chat_id = int(MAIN_ADMIN) if MAIN_ADMIN.isdigit() else MAIN_ADMIN
            await app.send_sticker(chat_id ,sticker=random.choice(saludos))
            await app.send_message(chat_id=chat_id, text=f"Bot @{app.me.username} iniciado")
        except Exception as e:
            print(f"Error al enviar el mensaje al MAIN_ADMIN: {e}")

@app.on_callback_query(filters.regex("^(cbz|pdf|fotos)"))
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    protect_content = PROTECT_CONTENT and user_id not in allowed_ids
    await manejar_opcion(client, callback_query, protect_content, user_id)

@app.on_callback_query()
async def help_callback_handler(client, callback_query):
    await handle_help_callback(client, callback_query)
    
async def main():
    await app.start()
    if MAIN_ADMIN:
        await notify_main_admin()
    print("Bot iniciado y operativo.")

    # Mantén el bot corriendo hasta que se detenga manualmente
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Detención forzada realizada")
