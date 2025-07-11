import os
import asyncio
import nest_asyncio
import re
from pyrogram import Client
from pyrogram.types import Message
from command.moodleclient import upload_token
from command.htools import nh_combined_operation, cambiar_default_selection
from command.admintools import add_user, remove_user, add_chat, remove_chat, ban_user, deban_user, handle_start
from command.imgtools import create_imgchest_post
from command.webtools import handle_scan, handle_multiscan, summarize_lines
from command.mailtools import send_mail, set_mail, verify_mail, set_mail_limit, set_mail_delay, multisetmail, multisendmail
from command.videotools import update_video_settings, compress_video, cancelar_tarea, listar_tareas, cambiar_miniatura
from command.filetools import handle_compress, rename, set_size, caption
from command.telegramtools import get_file_id, send_file_by_id
from command.help import handle_help, handle_help_callback  # Importar funciones de ayuda desde help.py

nest_asyncio.apply()

# Definir usuarios administradores y VIPs
admin_users = list(map(int, os.getenv('ADMINS', '').split(','))) if os.getenv('ADMINS') else []
vip_users = list(map(int, os.getenv('VIP_USERS', '').split(','))) if os.getenv('VIP_USERS') else []

# Definir lista de IDs permitidos (allowed_ids)
allowed_ids = set(admin_users).union(set(vip_users))

# Revisar PROTECT_CONTENT
protect_content_env = os.getenv('PROTECT_CONTENT', '').strip().lower()
is_protect_content_enabled = protect_content_env == 'true'  # Evaluamos si es "True" en cualquier formato
auto_users = {}

async def process_command(client: Client, message: Message, active_cmd: str, admin_cmd: str, user_id: int, username: str, chat_id: int):
    global allowed_ids
    text = message.text.strip().lower() if message.text else ""
    if not is_protect_content_enabled and user_id not in allowed_ids:
        allowed_ids = allowed_ids.union({user_id})
    #user_id = message.from_user.id
    auto = auto_users.get(user_id, False)
    
    def cmd(command_env, is_admin=False, is_vip=False):
        return (
            active_cmd == "all" or 
            command_env in active_cmd or 
            ((is_admin or is_vip) and (admin_cmd == "all" or command_env in admin_cmd))
        )

    if text.startswith("/start"):
        await asyncio.create_task(handle_start(client, message))
    
    elif text.startswith("/help"):  # Manejo del comando /help
        await asyncio.create_task(handle_help(client, message))
        return
    
    elif text.startswith(("/nh", "/3h", "/cover", "/covernh", "/setfile")):
        if cmd("htools", user_id in admin_users, user_id in vip_users):
            # Comando /setfile
            global link_type
            if text.startswith("/setfile"):
                parts = text.split(maxsplit=1)
                if len(parts) > 1:
                    new_selection = parts[1].strip().lower()
                    if new_selection in ["none", "cbz", "pdf", "both"]:
                        if new_selection == "none":
                            new_selection = None
                        else:
                            new_selection = new_selection.upper()  # Convertimos CBZ y PDF a mayúsculas
                        cambiar_default_selection(user_id, new_selection)
                        await message.reply(f"¡Selección predeterminada cambiada a '{new_selection if new_selection else 'None'}'!")
                    else:
                        await message.reply("Opción inválida. Usa: '/setfile cbz', '/setfile pdf', '/setfile both' o '/setfile none'.")
                else:
                    await message.reply(
                        "Usa uno de los siguientes comandos para cambiar la selección predeterminada:\n\n"
                        "`/setfile cbz` - Configurar como CBZ\n"
                        "`/setfile pdf` - Configurar como PDF\n"
                        "`/setfile both` - Configurar como ambos\n"
                        "`/setfile none` - Eliminar la selección predeterminada"
                    )
                return

            # Comando /nh
            elif text.startswith("/nh"):
                parts = text.split(maxsplit=1)
                codes = parts[1].split(',') if len(parts) > 1 and ',' in parts[1] else [parts[1]] if len(parts) > 1 else []
                codes_limpiados = [re.sub(r"https://nhentai\.net|https://[a-z]{2}\.3hentai\.net|https://3hentai\.net|/d/|/g/|/", "", code).strip() for code in codes]
                if codes_limpiados != codes:
                    codes = codes_limpiados
                    await message.reply("Solo son necesarios los números pero ok")
                
                #global link_type
                link_type = "nh"
                operation_type = "download"
                protect_content = user_id not in allowed_ids
                await asyncio.create_task(nh_combined_operation(client, message, codes, link_type, protect_content, user_id, operation_type))
                return

            # Comando /3h
            elif text.startswith("/3h"):
                parts = text.split(maxsplit=1)
                codes = parts[1].split(',') if len(parts) > 1 and ',' in parts[1] else [parts[1]] if len(parts) > 1 else []
                codes_limpiados = [re.sub(r"https://nhentai\.net|https://[a-z]{2}\.3hentai\.net|https://3hentai\.net|/d/|/g/|/", "", code).strip() for code in codes]
                if codes_limpiados != codes:
                    codes = codes_limpiados
                    await message.reply("Solo son necesarios los números pero ok")
                    
                #global link_type
                link_type = "3h"
                operation_type = "download"
                protect_content = user_id not in allowed_ids
                await asyncio.create_task(nh_combined_operation(client, message, codes, link_type, protect_content, user_id, operation_type))
                return

            # Comando /cover3h
            elif text.startswith(("/cover3h")):
                parts = text.split(maxsplit=1)
                codes = parts[1].split(',') if len(parts) > 1 and ',' in parts[1] else [parts[1]] if len(parts) > 1 else []
                codes_limpiados = [re.sub(r"https://nhentai\.net|https://[a-z]{2}\.3hentai\.net|https://3hentai\.net|/d/|/g/|/", "", code).strip() for code in codes]
                if codes_limpiados != codes:
                    codes = codes_limpiados
                    await message.reply("Solo son necesarios los números pero ok")
                    
                #global link_type
                link_type = "3h"
                operation_type = "cover"
                protect_content = user_id not in allowed_ids
                await asyncio.create_task(nh_combined_operation(client, message, codes, link_type, protect_content, user_id, operation_type))
                return

            # Comando /covernh
            elif text.startswith("/covernh"):
                parts = text.split(maxsplit=1)
                codes = parts[1].split(',') if len(parts) > 1 and ',' in parts[1] else [parts[1]] if len(parts) > 1 else []
                codes_limpiados = [re.sub(r"https://nhentai\.net|https://[a-z]{2}\.3hentai\.net|https://3hentai\.net|/d/|/g/|/", "", code).strip() for code in codes]
                if codes_limpiados != codes:
                    codes = codes_limpiados
                    await message.reply("Solo son necesarios los números pero ok")
                    
                #global link_type
                link_type = "nh"
                operation_type = "cover"
                protect_content = user_id not in allowed_ids
                await asyncio.create_task(nh_combined_operation(client, message, codes, link_type, protect_content, user_id, operation_type))
                return

    elif text.startswith("/imgchest"):
        if cmd("imgtools", user_id in admin_users, user_id in vip_users):
            if message.reply_to_message and (message.reply_to_message.photo or message.reply_to_message.document or message.reply_to_message.video):
                await asyncio.create_task(create_imgchest_post(client, message))
            else:
                await message.reply("Por favor, usa el comando respondiendo a una foto.")
        return

    
    elif text.startswith(("/setmail", "/sendmail", "/verify", "/setmb", "/setdelay", "multisetmail", "multisendmail")):
        if cmd("mailtools", user_id in admin_users, user_id in vip_users):
            if text.startswith("/setmail"):
                await asyncio.create_task(set_mail(client, message))

            elif text.startswith("/multisetmail"):
                await asyncio.create_task(multisetmail(client, message))

            elif text.startswith("/multisendmail"):
                await asyncio.create_task(multisendmail(client, message))
                

            elif text.startswith("/sendmail"):
                try:
                    parts = text.split()
                    repeats = int(parts[1]) if len(parts) > 1 else 1
                    repeats = min(repeats, 99999)

                    for i in range(repeats):
                        await asyncio.create_task(send_mail(client, message))
                        await asyncio.sleep(1)
                except Exception as e:
                    await message.reply(f"Error en /sendmail: {e}")

            elif text.startswith("/setmb"):
                await asyncio.create_task(set_mail_limit(client, message))

            elif text.startswith("/setdelay"):
                await asyncio.create_task(set_mail_delay(client, message))
                
            elif text.startswith("/verify"):
                await asyncio.create_task(verify_mail(client, message))
        return

    elif text.startswith(("/id", "/sendid")):
        if text.startswith("/id"):
            await asyncio.create_task(get_file_id(client, message))
            return
        elif text.startswith("/sendid"):
            await asyncio.create_task(send_file_by_id(client, message))
            return
            
    elif text.startswith(("/compress", "/setsize", "/rename", "/caption")):
        if cmd("filetools", user_id in admin_users, user_id in vip_users):
            if text.startswith("/compress"):
                await asyncio.create_task(handle_compress(client, message, username))
            elif text.startswith("/setsize"):
                await asyncio.create_task(set_size(client, message))
            elif text.startswith("/rename"):
                await asyncio.create_task(rename(client, message))
            elif text.startswith(("/caption")):
                if not message.reply_to_message:
                    await message.reply("Responda a un mensaje con archivo para usarlo")
                    return
                original_caption = message.reply_to_message.caption if message.reply_to_message.caption else ""
                if original_caption.startswith("Look Here"):
                    await message.reply("No puedo realizar esa acción")
                    return
                file_id = None
                if message.reply_to_message.document:
                    file_id = message.reply_to_message.document.file_id
                elif message.reply_to_message.photo:
                    file_id = message.reply_to_message.photo.file_id
                elif message.reply_to_message.video:
                    file_id = message.reply_to_message.video.file_id
                elif message.reply_to_message.audio:
                    file_id = message.reply_to_message.audio.file_id
                elif message.reply_to_message.voice:
                    file_id = message.reply_to_message.voice.file_id
                elif message.reply_to_message.animation:
                    file_id = message.reply_to_message.animation.file_id
                
                if not file_id:
                    await message.reply("Responda a un mensaje con archivo multimedia válido para usarlo")
                    return
                
                # Captura el texto después del comando como subtítulo
                caption_text = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else "Archivo reenviado"
                
                # Reenviar el archivo según su tipo con el caption
                await caption(client, message.chat.id, file_id, caption_text)
        return


    elif text.startswith(("/convert", "/calidad", "/autoconvert", "/cancel", "/list", "/miniatura")) or \
       ((message.video is not None) or (message.document and message.document.mime_type and message.document.mime_type.startswith("video/"))) or \
       (message.photo and message.caption and message.caption.startswith("/miniatura")):
        if cmd("videotools", user_id in admin_users, user_id in vip_users):
            if text.startswith("/convert"):
                if message.reply_to_message and (message.reply_to_message.video or (message.reply_to_message.document and message.reply_to_message.mime_type.startswith("video/"))):
                    await asyncio.create_task(compress_video(admin_users, client, message, allowed_ids))

            elif text.startswith("/autoconvert"):
                # Activar/desactivar "auto" para este usuario
                if user_id in auto_users and auto_users[user_id]:
                    auto_users[user_id] = False
                    await client.send_message(
                        chat_id=message.chat.id,
                        text="🛑 Modo automático desactivado.",
                        protect_content=False
                    )
                else:
                    auto_users[user_id] = True
                    await client.send_message(
                        chat_id=message.chat.id,
                        text="✅ Modo automático activado.",
                        protect_content=False
                    )

            elif text.startswith("/calidad"):
                await asyncio.create_task(update_video_settings(client, message, allowed_ids))

            elif text.startswith("/cancel"):
                try:
                    task_id = text.split(" ", 1)[1].strip()
                    await cancelar_tarea(admin_users, client, task_id, message.chat.id, message, allowed_ids)
                except IndexError:
                    await client.send_message(
                        chat_id=message.chat.id,
                        text="⚠️ Debes proporcionar un ID válido para cancelar la tarea. Ejemplo: `/cancel <ID>`",
                        protect_content=True
                    )

            elif text.startswith("/miniatura") or (message.photo and message.caption and message.caption.startswith("/miniatura")):
                await cambiar_miniatura(client, message)

            elif text.startswith("/list"):
                if user_id in admin_users or user_id in vip_users:
                    await listar_tareas(client, chat_id, allowed_ids, message)
                else:
                    await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para usar este comando.")

            elif auto and (message.video or (message.document and message.document.mime_type.startswith("video/"))):
                await asyncio.create_task(compress_video(admin_users, client, message, allowed_ids))



    elif text.startswith(("/scan", "/multiscan", "/resumecodes", "/resumetxtcodes")):
        if cmd("webtools", user_id in admin_users, user_id in vip_users):
            if text.startswith("/scan"):
                await asyncio.create_task(handle_scan(client, message))
            elif text.startswith("/multiscan"):
                await asyncio.create_task(handle_multiscan(client, message))
            elif text.startswith("/resumecodes") and message.reply_to_message and message.reply_to_message.document:
                file_path = await client.download_media(message.reply_to_message.document)
                if not file_path.endswith(".txt"):
                    os.remove(file_path)
                    await message.reply("Solo usar con TXT.")
                    return
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines()]
                codes = await summarize_lines(lines)
                if codes:
                    codes_list = codes.split(", ")
                    for i in range(0, len(codes_list), 25):
                        await message.reply(", ".join(codes_list[i:i+25]))
                else:
                    await message.reply("No se encontraron códigos en el archivo.")
                os.remove(file_path)
            elif text.startswith("/resumetxtcodes") and message.reply_to_message and message.reply_to_message.document:
                file_path = await client.download_media(message.reply_to_message.document)
                if not file_path.endswith(".txt"):
                    os.remove(file_path)
                    await message.reply("Solo usar con TXT.")
                    return
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines()]
                codes = await summarize_lines(lines)
                if codes:
                    txt_file_path = "codes_summary.txt"
                    with open(txt_file_path, "w", encoding="utf-8") as txt_file:
                        txt_file.write(codes)
                    await client.send_document(chat_id=message.chat.id, document=txt_file_path, caption="Aquí están todos los códigos.")
                    os.remove(txt_file_path)
                else:
                    await message.reply("No se encontraron códigos en el archivo.")
                os.remove(file_path)
        return
    
    elif text.startswith(("/adduser", "/remuser", "/addchat", "/remchat", "/ban", "/unban")) and user_id in admin_users:
        if text.startswith("/adduser"):
            await asyncio.create_task(add_user(client, message, user_id, chat_id))
        elif text.startswith("/remuser"):
            await asyncio.create_task(remove_user(client, message, user_id, chat_id))
        elif text.startswith("/addchat"):
            await asyncio.create_task(add_chat(client, message, user_id, chat_id))
        elif text.startswith("/remchat"):
            await asyncio.create_task(remove_chat(client, message, user_id, chat_id))
        elif text.startswith("/ban"):
            await asyncio.create_task(ban_user(client, message, user_id, chat_id))
        elif text.startswith("/unban"):
            await asyncio.create_task(deban_user(client, message, user_id, chat_id))
        return
            
