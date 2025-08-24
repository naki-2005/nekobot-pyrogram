import os
import asyncio
import nest_asyncio
import re
from pyrogram import Client
from pyrogram.types import Message
from command.moodleclient import upload_token
from command.htools import safe_call, nh_combined_operation, nh_combined_operation_txt, cambiar_default_selection
from command.admintools import send_access_editor, send_setting_editor, handle_start
from command.imgtools import create_imgchest_post
from command.webtools import handle_scan, handle_multiscan, summarize_lines, split_codes
from command.mailtools.set_values import set_mail, verify_mail, set_mail_limit, set_mail_delay, multisetmail, copy_manager, mydata
from command.mailtools.send import send_mail, multisendmail
from command.videotools import update_video_settings, compress_video, cancelar_tarea, listar_tareas, cambiar_miniatura
from command.filetools import handle_compress, rename, set_size, caption
from command.telegramtools import get_file_id, send_file_by_id
from command.help import handle_help, handle_help_callback 
from command.get_files.txt_a_cbz import txt_a_cbz
from pyrogram.enums import ChatType
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

async def process_command(
    client: Client,
    message: Message,
    active_cmd: str,
    admin_cmd: str,
    user_id: int,
    username: str,
    chat_id: int,
    int_lvl: int
):
    global allowed_ids
    text = message.text.strip().lower() if message.text else ""
    if message.from_user is None:
        return

    user_id = message.from_user.id
    auto = auto_users.get(user_id, False)
    protect_content = int_lvl < 3

    if not is_protect_content_enabled and protect_content:
        protect_content = False

    is_vip = int_lvl >= 3
    is_mod = int_lvl >= 4
    is_admin = int_lvl >= 5
    is_owner = int_lvl == 6

    def cmd(command_env, is_admin=is_admin, is_vip=is_vip):
        return (
            active_cmd == "all" or 
            command_env in active_cmd or 
            ((is_admin or is_vip) and (admin_cmd == "all" or command_env in admin_cmd))
        )

    command = text.split()[0] if text else ""

    if command == "/start":
        await asyncio.create_task(handle_start(client, message))

    elif command == "/help":
        await asyncio.create_task(handle_help(client, message))
        return
        
    elif command in ("/nh", "/3h", "/cover3h", "/covernh", "/setfile", "/nhtxt", "/3htxt", "/dltxt"):
        if cmd("htools", user_id in admin_users, user_id in vip_users):
            reply = message.reply_to_message
            parts = text.split(maxsplit=1)
            arg_text = parts[1] if len(parts) > 1 else ""
            codes = arg_text.split(',') if ',' in arg_text else [arg_text] if arg_text else []
            codes_limpiados = [
                re.sub(
                    r"https://nhentai\.net|https://[a-z]{2}\.3hentai\.net|https://3hentai\.net|/d/|/g/|/",
                    "",
                    code
                ).strip()
                for code in codes
            ]

            if codes_limpiados != codes:
                codes = codes_limpiados
                await message.reply("Solo son necesarios los números pero ok")

            if command == "/setfile":
                new_selection = arg_text.strip().lower()
                valid_options = ["none", "cbz", "pdf", "both"]
                if new_selection in valid_options:
                    selection = None if new_selection == "none" else new_selection.upper()
                    cambiar_default_selection(user_id, selection)
                    await message.reply(f"¡Selección predeterminada cambiada a '{selection if selection else 'None'}'!")
                else:
                    await message.reply(
                        "Opción inválida. Usa: '/setfile cbz', '/setfile pdf', '/setfile both' o '/setfile none'."
                    )
                return

            elif command == "/nh":
                await asyncio.create_task(
                    nh_combined_operation(client, message, codes, "nh", protect_content, user_id, "download")
                )
                return

            elif command == "/3h":
                await asyncio.create_task(
                    nh_combined_operation(client, message, codes, "3h", protect_content, user_id, "download")
                )
                return

            elif command == "/cover3h":
                await asyncio.create_task(
                    nh_combined_operation(client, message, codes, "3h", protect_content, user_id, "cover")
                )
                return

            elif command == "/covernh":
                await asyncio.create_task(
                    nh_combined_operation(client, message, codes, "nh", protect_content, user_id, "cover")
                )
                return

            elif command == "/nhtxt":
                await asyncio.create_task(
                    nh_combined_operation_txt(client, message, "nh", protect_content, user_id, "download")
                )
                return

            elif command == "/3htxt":
                await asyncio.create_task(
                    nh_combined_operation_txt(client, message, "3h", protect_content, user_id, "download")
                )
                return
            elif command == "/dltxt" and reply and reply.document:
                path_txt = await client.download_media(reply.document)
                if not path_txt or not path_txt.endswith(".txt"):
                    if path_txt:
                        os.remove(path_txt)
                    await message.reply("Solo usar con archivos .txt")
                    return

                
                path_cbz = txt_a_cbz(path_txt)
                await safe_call(client.send_document,
                        chat_id=message.chat.id,
                        document=path_cbz,
                               )


    elif command == "/imgchest":
        if cmd("imgtools", user_id in admin_users, user_id in vip_users):
            reply = message.reply_to_message
            if reply and (reply.photo or reply.document or reply.video):
                await asyncio.create_task(create_imgchest_post(client, message))
            else:
                await message.reply("Por favor, usa el comando respondiendo a una foto.")
        return

    elif command in ("/compress", "/split", "/setsize", "/rename", "/caption"):
        if cmd("filetools", user_id in admin_users, user_id in vip_users):
            if command == "/compress":
                await handle_compress(client, message, username, type="7z")

            elif command == "/split":
                await handle_compress(client, message, username, type="bites")

            elif command == "/setsize":
                await set_size(client, message)

            elif command == "/rename":
                await rename(client, message)

            elif command == "/caption":
                reply = message.reply_to_message
                if not reply:
                    await message.reply("Responda a un mensaje con archivo para usarlo")
                    return

                original_caption = reply.caption or ""
                if original_caption.startswith("Look Here"):
                    await message.reply("No puedo realizar esa acción")
                    return

                file_id = None
                for attr in ("document", "photo", "video", "audio", "voice", "animation"):
                    media = getattr(reply, attr, None)
                    if media:
                        file_id = media.file_id
                        break

                if not file_id:
                    await message.reply("Responda a un mensaje con archivo multimedia válido para usarlo")
                    return

                caption_text = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else "Archivo reenviado"
                await caption(client, chat_id, file_id, caption_text)
        return
    elif command in ("/mydata", "/setmail", "/sendmail", "/sendmailb", "/verify", "/setmb", "/setdelay", "/multisetmail", "/multisendmail", "/savemail", "/mailcopy"):
        if cmd("mailtools", user_id in admin_users, user_id in vip_users):
            parts = text.split()
            arg = parts[1] if len(parts) > 1 else ""
            repeats = min(int(arg), 99999) if arg.isdigit() else 1

            if command == "/setmail":
                await asyncio.create_task(set_mail(client, message))

            elif command == "/mydata":
                await asyncio.create_task(mydata(client, message))

            elif command == "/multisetmail":
                await asyncio.create_task(multisetmail(client, message))

            elif command == "/multisendmail":
                await asyncio.create_task(multisendmail(client, message))

            elif command == "/sendmailb":
                try:
                    for _ in range(repeats):
                        await asyncio.create_task(send_mail(client, message, division="bites"))
                        await asyncio.sleep(1)
                except Exception as e:
                    await message.reply(f"Error en /sendmailb: {e}")

            elif command == "/sendmail":
                try:
                    for _ in range(repeats):
                        await asyncio.create_task(send_mail(client, message, division="7z"))
                        await asyncio.sleep(1)
                except Exception as e:
                    await message.reply(f"Error en /sendmail: {e}")

            elif command == "/setmb":
                await asyncio.create_task(set_mail_limit(client, message))

            elif command == "/setdelay":
                await asyncio.create_task(set_mail_delay(client, message))

            elif command == "/verify":
                await asyncio.create_task(verify_mail(client, message))

            elif command == "/mailcopy":
                respuesta = await asyncio.create_task(copy_manager(user_id))
                await message.reply(respuesta)
        return

    elif command in ("/id", "/sendid"):
        if command == "/id":
            await asyncio.create_task(get_file_id(client, message))
        elif command == "/sendid":
            await asyncio.create_task(send_file_by_id(client, message))
        return
                        
    elif command in ("/compress", "/split", "/setsize", "/rename", "/caption"):
        if cmd("filetools", user_id in admin_users, user_id in vip_users):
            parts = text.split(maxsplit=1)
            arg = parts[1] if len(parts) > 1 else ""
            reply = message.reply_to_message

            if command == "/compress":
                await handle_compress(client, message, username, type="7z")

            elif command == "/split":
                await handle_compress(client, message, username, type="bites")

            elif command == "/setsize":
                await set_size(client, message)

            elif command == "/rename":
                await rename(client, message)

            elif command == "/caption":
                if not reply:
                    await message.reply("Responda a un mensaje con archivo para usarlo")
                    return

                original_caption = reply.caption or ""
                if original_caption.startswith("Look Here"):
                    await message.reply("No puedo realizar esa acción")
                    return

                file_id = None
                for attr in ("document", "photo", "video", "audio", "voice", "animation"):
                    media = getattr(reply, attr, None)
                    if media:
                        file_id = media.file_id
                        break

                if not file_id:
                    await message.reply("Responda a un mensaje con archivo multimedia válido para usarlo")
                    return

                caption_text = arg if arg else "Archivo reenviado"
                await caption(client, message.chat.id, file_id, caption_text)
        return


    elif command in ("/convert", "/calidad", "/autoconvert", "/cancel", "/list", "/miniatura") or \
         ((message.video is not None) or (message.document and message.document.mime_type and message.document.mime_type.startswith("video/"))) or \
         (message.photo and message.caption and message.caption.startswith("/miniatura")):
        if cmd("videotools", user_id in admin_users, user_id in vip_users):
            parts = text.split(maxsplit=1)
            arg = parts[1] if len(parts) > 1 else ""

            if command == "/convert":
                reply = message.reply_to_message
                if reply and (reply.video or (reply.document and reply.document.mime_type.startswith("video/"))):
                    await asyncio.create_task(compress_video(admin_users, client, message, allowed_ids))

            elif command == "/autoconvert":
                auto_users[user_id] = not auto_users.get(user_id, False)
                status = "✅ Modo automático activado." if auto_users[user_id] else "🛑 Modo automático desactivado."
                await client.send_message(chat_id=message.chat.id, text=status, protect_content=False)

            elif command == "/calidad":
                await asyncio.create_task(update_video_settings(client, message, allowed_ids))

            elif command == "/cancel":
                try:
                    task_id = arg.strip()
                    await cancelar_tarea(admin_users, client, task_id, message.chat.id, message, allowed_ids)
                except IndexError:
                    await client.send_message(
                        chat_id=message.chat.id,
                        text="⚠️ Debes proporcionar un ID válido para cancelar la tarea. Ejemplo: `/cancel <ID>`",
                        protect_content=True
                    )

            elif command == "/miniatura" or (message.photo and message.caption and message.caption.startswith("/miniatura")):
                await cambiar_miniatura(client, message)

            elif command == "/list":
                if user_id in admin_users or user_id in vip_users:
                    await listar_tareas(client, chat_id, allowed_ids, message)
                else:
                    await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para usar este comando.")

            elif auto and (message.video or (message.document and message.document.mime_type.startswith("video/"))):
                await asyncio.create_task(compress_video(admin_users, client, message, allowed_ids))
        return

    elif command in ("/scan", "/multiscan", "/resumecodes", "/resumetxtcodes", "/codesplit"):
        if cmd("webtools", user_id in admin_users, user_id in vip_users):
            reply = message.reply_to_message
            if command == "/scan":
                await asyncio.create_task(handle_scan(client, message))

            elif command == "/multiscan":
                await asyncio.create_task(handle_multiscan(client, message))
            elif command == "/codesplit" and reply and reply.document:
                file_path = await client.download_media(reply.document)
                if not file_path or not file_path.endswith(".txt"):
                    if file_path:
                        os.remove(file_path)
                    await message.reply("Solo usar con archivos .txt generados por /resumetxtcodes.")
                    return

                parts = text.split()
                try:
                    chunk_size = int(parts[1]) if len(parts) > 1 else 1000
                    if chunk_size <= 0:
                        raise ValueError
                except ValueError:
                    os.remove(file_path)
                    await message.reply("Formato incorrecto. Usa: /codesplit <cantidad>, ej. /codesplit 1000")
                    return

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                except Exception:
                    os.remove(file_path)
                    await message.reply("Error al leer el archivo.")
                    return

                os.remove(file_path)

                if not content or "," not in content:
                    await message.reply("El archivo no contiene códigos válidos.")
                    return

                codes = [c.strip() for c in content.split(",") if c.strip()]
                if not codes:
                    await message.reply("No se encontraron códigos válidos.")
                    return

                file_paths = await split_codes(codes, chunk_size)

                for i, path in enumerate(file_paths):
                    caption = f"Parte {i+1} ({chunk_size} códigos máx)"
                    await client.send_document(chat_id=message.chat.id, document=path, caption=caption)
                    os.remove(path)

            elif command == "/resumecodes" and reply and reply.document:
                file_path = await client.download_media(reply.document)
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


            elif command == "/resumetxtcodes" and reply and reply.document:
                file_path = await client.download_media(reply.document)
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

    elif command == "/settings" and message.chat.type in (ChatType.PRIVATE, ChatType.BOT):
        await send_setting_editor(client, message)
        return

    elif command == "/edituser" and message.chat.type in (ChatType.PRIVATE, ChatType.BOT):
        await send_access_editor(client, message)
        return
