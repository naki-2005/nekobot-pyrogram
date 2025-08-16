import os
import random
from pyrogram import Client
from pyrogram.types import Message
from data.stickers import saludos
from command.help import handle_help_callback, handle_help
from data.vars import MAIN_ADMIN, CODEWORD, BOT_IS_PUBLIC, PROTECT_CONTENT
from data.data import modify_db

def is_env_admin(user_id):
    return str(user_id) in os.getenv("ADMINS", "").split(',')

# 🎉 Inicio
async def handle_start(client, message):
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    name = f"{first_name} {last_name}".strip()
    username = message.from_user.username or "Usuario"

    await client.send_sticker(message.chat.id, sticker=random.choice(saludos))
    response = (
        f"Bienvenido [{name}](https://t.me/{username}) a Nekobot. "
        "Para conocer los comandos escriba /help o visite la [página oficial](https://nakigeplayer.github.io/nekobot-pyrogram/)."
    )
    await message.reply(response, disable_web_page_preview=True)

# 👤 Añadir usuario temporal
async def add_user(client, message, user_id, chat_id):
    new_user_id = int(message.text.split()[1])
    modify_db("INSERT OR IGNORE INTO temp_users (user_id) VALUES (?)", (new_user_id,))
    modify_db("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (new_user_id,))
    await message.reply(f"Usuario {new_user_id} añadido temporalmente.")

# 👤 Eliminar usuario temporal
async def remove_user(client, message, user_id, chat_id):
    rem_user_id = int(message.text.split()[1])
    modify_db("DELETE FROM temp_users WHERE user_id = ?", (rem_user_id,))
    modify_db("DELETE FROM allowed_users WHERE user_id = ?", (rem_user_id,))
    await message.reply(f"Usuario {rem_user_id} eliminado temporalmente.")

# 💬 Añadir chat temporal
async def add_chat(client, message, user_id, chat_id):
    modify_db("INSERT OR IGNORE INTO temp_chats (chat_id) VALUES (?)", (chat_id,))
    modify_db("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (chat_id,))
    await message.reply(f"Chat {chat_id} añadido temporalmente.")

# 💬 Eliminar chat temporal
async def remove_chat(client, message, user_id, chat_id):
    modify_db("DELETE FROM temp_chats WHERE chat_id = ?", (chat_id,))
    modify_db("DELETE FROM allowed_users WHERE user_id = ?", (chat_id,))
    await message.reply(f"Chat {chat_id} eliminado temporalmente.")

# 🚫 Banear usuario
async def ban_user(client, message, user_id, chat_id):
    ban_user_id = int(message.text.split()[1])
    if is_env_admin(ban_user_id):
        await message.reply("No puedes banear a un administrador de entorno.")
        return
    modify_db("INSERT OR IGNORE INTO ban_users (user_id) VALUES (?)", (ban_user_id,))
    await message.reply(f"Usuario {ban_user_id} baneado.")

# ✅ Desbanear usuario
async def deban_user(client, message, user_id, chat_id):
    deban_user_id = int(message.text.split()[1])
    modify_db("DELETE FROM ban_users WHERE user_id = ?", (deban_user_id,))
    await message.reply(f"Usuario {deban_user_id} desbaneado.")

# 🛡️ Añadir admin (solo si es admin de entorno)
async def add_admin(client, message, user_id, chat_id):
    if not is_env_admin(user_id):
        await message.reply("No tienes permiso para añadir administradores.")
        return
    new_admin_id = int(message.text.split()[1])
    modify_db("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin_id,))
    await message.reply(f"Administrador {new_admin_id} añadido.")

# 🧹 Eliminar admin (solo si es admin de entorno)
async def remove_admin(client, message, user_id, chat_id):
    if not is_env_admin(user_id):
        await message.reply("No tienes permiso para eliminar administradores.")
        return
    rem_admin_id = int(message.text.split()[1])
    modify_db("DELETE FROM admins WHERE user_id = ?", (rem_admin_id,))
    await message.reply(f"Administrador {rem_admin_id} eliminado.")

def read_db(query, params=()):
    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    # 📥 Descargar base
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            content = base64.b64decode(existing["content"])
            with open(FILE_PATH, "wb") as f:
                f.write(content)
    except Exception as e:
        raise RuntimeError(f"Error al leer la base: {e}")

    # 📤 Leer datos
    conn = sqlite3.connect(FILE_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]
            
