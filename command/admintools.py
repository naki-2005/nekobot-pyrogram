import os
from pyrogram import Client
from pyrogram.types import Message
import asyncio
from data.stickers import saludos
import random 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from command.help import handle_help_callback, handle_help
from data.vars import api_id, api_hash, bot_token, admin_users, users, temp_users, temp_chats, vip_users, ban_users, MAIN_ADMIN, CODEWORD, BOT_IS_PUBLIC, PROTECT_CONTENT, allowed_ids, allowed_users
from command.mailtools.db import save_user_data_to_db, load_user_config


async def handle_start(client, message):
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    name = f"{first_name} {last_name}".strip()  # Combina nombres y elimina espacios extra
    username = message.from_user.username or "Usuario"

    await client.send_sticker(message.chat.id, sticker=random.choice(saludos))
    response = (
        f"Bienvenido [{name}](https://t.me/{username}) a Nekobot. "  # Enlace al perfil
        "Para conocer los comandos escriba /help o visite la [página oficial](https://nakigeplayer.github.io/nekobot-pyrogram/)."  # Enlace funcional
    )

    # Evita la vista previa de enlaces en el mensaje
    await message.reply(response, disable_web_page_preview=True)
    
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_access_buttons(user_lvl: str, target_id: int):
    buttons = []

    buttons.append([InlineKeyboardButton("❌ Banear", callback_data=f"id_{target_id}#0")])
    buttons.append([InlineKeyboardButton("🌐 Acceso público", callback_data=f"id_{target_id}#1")])
    buttons.append([InlineKeyboardButton("👤 Usuario", callback_data=f"id_{target_id}#2")])
    buttons.append([InlineKeyboardButton("⭐ Usuario VIP", callback_data=f"id_{target_id}#3")])

    if user_lvl in ["5", "6"]:
        buttons.append([InlineKeyboardButton("🛠️ Administrador", callback_data=f"id_{target_id}#4")])

    if user_lvl == "6":
        buttons.append([InlineKeyboardButton("👑 ADMIN", callback_data=f"id_{target_id}#5")])

    return InlineKeyboardMarkup(buttons)

async def send_access_editor(client, message):
    user_id = message.from_user.id
    try:
        target_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply("⚠️ Debes especificar un ID válido.")
        return

    try:
        user_lvl = load_user_config(user_id, "lvl")
        if not user_lvl or int(user_lvl) < 4:
            return
    except Exception as e:
        await message.reply(f"⚠️ Error al cargar tu nivel: {e}")
        return

    try:
        target_lvl = load_user_config(target_id, "lvl")
    except:
        target_lvl = "1"

    try:
        if int(target_lvl) >= int(user_lvl):
            await message.reply("🚫 No puedes editar el acceso de este usuario.")
            return
    except ValueError:
        await message.reply("❌ Nivel inválido.")
        return

    markup = get_access_buttons(user_lvl, target_id)
    await message.reply(f"⚙️ Editar el nivel de acceso del usuario `{target_id}`", reply_markup=markup)
    
async def process_access_callback(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    try:
        raw_id, new_lvl_str = data.split("#")
        target_id = int(raw_id.replace("id_", ""))
        new_lvl = str(new_lvl_str)
    except Exception:
        await callback_query.answer("❌ Callback inválido", show_alert=True)
        return

    try:
        save_user_data_to_db(target_id, "lvl", new_lvl)
        await callback_query.answer(f"✅ Nivel actualizado a {get_access_label(new_lvl)}", show_alert=True)

        await callback_query.message.edit_text(
            f"✅ El nivel de acceso de `{target_id}` ha sido actualizado a: {get_access_label(new_lvl)}",
            reply_markup=None
        )
    except Exception as e:
        await callback_query.answer(f"⚠️ Error al guardar: {e}", show_alert=True)
        
