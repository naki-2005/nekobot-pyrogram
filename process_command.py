import os
import asyncio
import nest_asyncio
import re
import sqlite3
import subprocess
from pyrogram import Client
from pyrogram.types import Message
from command.moodleclient import upload_token
from command.htools import safe_call, nh_combined_operation, nh_combined_operation_txt, cambiar_default_selection
from command.admintools import send_access_editor, send_setting_protect, send_setting_editor, send_setting_public, guardar_parametro, handle_start
from command.imgtools import create_imgchest_post
from command.webtools import handle_scan, handle_multiscan, summarize_lines, split_codes
from command.mailtools.set_values import set_mail, verify_mail, set_mail_limit, set_mail_delay, multisetmail, copy_manager, mydata
from command.mailtools.send import send_mail, multisendmail
from command.videotools import update_video_settings, compress_video, cancelar_tarea, listar_tareas, cambiar_miniatura
from command.filetools import handle_compress, rename, set_size, caption
from command.telegramtools import get_file_id, send_file_by_id
from command.help import handle_help, handle_help_callback 
from command.get_files.txt_a_cbz import txt_a_cbz
from command.torrets_tools import handle_torrent_command
from command.filetolink import handle_up_command, clear_vault_files, list_vault_files, send_vault_file_by_index
from command.get_files.hitomi import descargar_y_comprimir_hitomi
from pyrogram.enums import ChatType
from pyrogram import enums
import time
nest_asyncio.apply()

BASE_DIR = "vault_files/torrent_dl"

def is_bot_protect() -> bool:
    ruta_db = os.path.join(os.getcwd(), 'bot_cmd.db')
    if not os.path.exists(ruta_db):
        return False

    try:
        conn = sqlite3.connect(ruta_db)
        cursor = conn.cursor()
        cursor.execute('SELECT valor FROM parametros WHERE nombre = ?', ('protect',))
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            return False

        return int(resultado[0]) == 2

    except Exception as e:
        print(f"[!] Error al acceder a bot_cmd.db: {e}")
        return False
        

auto_users = {}
import sqlite3
import os

def cmd(command_env: str, int_lvl: int) -> bool:
    if int_lvl == 6:
        return True

    ruta_db = os.path.join(os.getcwd(), 'bot_cmd.db')
    if not os.path.exists(ruta_db):
        return False 

    try:
        conn = sqlite3.connect(ruta_db)
        cursor = conn.cursor()
        cursor.execute('SELECT valor FROM parametros WHERE nombre = ?', (command_env,))
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            return False

        valor = int(resultado[0]) 

        if int_lvl in [1, 2]:
            return valor == 1
        elif int_lvl in [3, 4, 5]:
            return valor < 3 
        else:
            return False 

    except Exception as e:
        print(f"[!] Error al acceder to bot_cmd.db: {e}")
        return False
        
async def process_command(
    client: Client,
    message: Message,
    user_id: int,
    username: str,
    chat_id: int,
    int_lvl: int
):
    textori = message.text.strip() if message.text else ""
    text = textori.lower()
    if message.from_user is None:
        return

    user_id = message.from_user.id
    auto = auto_users.get(user_id, False)
    protect_content = int_lvl < 3

    if not is_bot_protect() and protect_content:
        protect_content = False

    is_vip = int_lvl >= 3
    is_mod = int_lvl >= 4
    is_admin = int_lvl >= 5
    is_owner = int_lvl == 6

    command = text.split()[0] if text else ""

    if command == "/start":
        await asyncio.create_task(handle_start(client, message))

    elif command == "/mydata":
        await asyncio.create_task(mydata(client, message))
        
    elif command == "/help":
        await asyncio.create_task(handle_help(client, message))
        return

    elif command == "/magnet":
        if cmd("torrent", int_lvl):
            parts = text.strip().split(maxsplit=2)
            if len(parts) < 2:
                await message.reply("❗ Debes proporcionar un enlace magnet o .torrent.")
                return

            use_compression = False
            if parts[1] == "-z":
                use_compression = True
                if len(parts) < 3:
                    await message.reply("❗ Debes proporcionar un enlace después de -z.")
                    return
                arg_text = parts[2]
            else:
                arg_text = parts[1]

            if not (arg_text.startswith("magnet:") or arg_text.endswith(".torrent")):
                await message.reply("❗ El enlace debe ser un magnet o un archivo .torrent.")
                return

            message.text = f"/magnet {arg_text}"
            status_msg = await message.reply("⏳ Iniciando descarga...")

            start_time = time.time()
            progress_data = {"filename": "", "percent": 0, "speed": 0.0}

            async def update_progress():
                while progress_data["percent"] < 100:
                    elapsed = int(time.time() - start_time)
                    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
                    speed_mb = round(progress_data["speed"] / 1024, 2)
                    await status_msg.edit_text(
                        f"📥 Descargando: {progress_data['filename']}\n"
                        f"📊 Progreso: {progress_data['percent']}%\n"
                        f"⏱️ Tiempo: {h:02d}:{m:02d}:{s:02d}\n"
                        f"🚀 Velocidad: {speed_mb} MB/s"
                    )
                    await asyncio.sleep(10)

            progress_task = asyncio.create_task(update_progress())
            files = await handle_torrent_command(client, message, progress_data)
            progress_data["percent"] = 100
            await progress_task
            await asyncio.sleep(5)
            await status_msg.delete()

            if not files:
                await message.reply("❌ No se descargaron archivos.")
                return

            if use_compression:
                try:
                    await client.send_chat_action(chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                    await message.reply("🗜️ Comprimiendo archivos en partes de 2000MB con 7z...")

                    archive_path = os.path.join(BASE_DIR, "compressed.7z")
                    seven_zip_exe = os.path.join("7z", "7zz")

                    cmd_args = [
                        seven_zip_exe,
                        'a',
                        '-mx=0',
                        '-v2000m',
                        archive_path,
                        os.path.join(BASE_DIR, '*')
                    ]

                    subprocess.run(cmd_args, check=True)

                    for rel_path in files:
                        path = os.path.join(BASE_DIR, rel_path)
                        if os.path.exists(path):
                            os.remove(path)

                    for part_file in sorted(os.listdir(BASE_DIR)):
                        full_path = os.path.join(BASE_DIR, part_file)
                        if part_file.startswith("compressed.7z"):
                            await client.send_chat_action(chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                            await client.send_document(chat_id, document=full_path)
                            await client.send_chat_action(chat_id, enums.ChatAction.CANCEL)
                            os.remove(full_path)

                except Exception as e:
                    await message.reply(f"⚠️ Error al comprimir y enviar archivos: {e}")
                return

            for rel_path in files:
                path = os.path.join(BASE_DIR, rel_path)
                try:
                    file_size = os.path.getsize(path)
                    if file_size > 2000 * 1024 * 1024:
                        await client.send_chat_action(chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await message.reply(f"📦 El archivo `{os.path.basename(path)}` excede los 2000MB. Dividiéndolo en partes...")

                        with open(path, 'rb') as original:
                            part_num = 1
                            while True:
                                part_data = original.read(2000 * 1024 * 1024)
                                if not part_data:
                                    break
                                part_file = f"{path}.{part_num:03d}"
                                with open(part_file, 'wb') as part:
                                    part.write(part_data)
                                await client.send_chat_action(chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                                await client.send_document(chat_id, document=part_file)
                                await client.send_chat_action(chat_id, enums.ChatAction.CANCEL)
                                os.remove(part_file)
                                part_num += 1

                        os.remove(path)
                    else:
                        await client.send_chat_action(chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await client.send_document(chat_id, document=path)
                        await client.send_chat_action(chat_id, enums.ChatAction.CANCEL)
                        os.remove(path)

                except Exception as e:
                    await message.reply(f"⚠️ Error al enviar {rel_path}: {e}")


                    
    elif command in ("/nh", "/3h", "/cover3h", "/covernh", "/setfile", "/nhtxt", "/3htxt", "/dltxt"):
        if cmd("htools", int_lvl):
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

    elif command == "/megadl":
        if not cmd("download", int_lvl):
            await message.reply("⛔ No tienes permiso para usar este comando.")
            return

        if len(text.split()) < 2:
            await message.reply("❌ Debes proporcionar un enlace de MEGA.")
            return

        mega_url = textori.split()[1]
        desmega_path = os.path.join("command", "desmega")
        output_dir = os.path.join("vault_files", "mega_dl")
        os.makedirs(output_dir, exist_ok=True)

        try:
            result = subprocess.run(
                [desmega_path, mega_url, "--path", output_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode != 0:
                await message.reply(f"❌ Error al ejecutar desmega:\n{result.stderr}")
                return

            files = os.listdir(output_dir)
            if not files:
                await message.reply("⚠️ No se encontró ningún archivo descargado.")
                return

            seven_zip_exe = os.path.join("7z", "7zz")

            for file_name in files:
                file_path = os.path.join(output_dir, file_name)
                if not os.path.isfile(file_path):
                    continue

                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

                if file_size_mb > 2000:
                    archive_base = os.path.join(output_dir, f"{file_name}_archive.7z")
                    cmd_args = [
                        seven_zip_exe,
                        'a',
                        '-mx=0',
                        f'-v2000m',
                        archive_base,
                        file_path
                    ]

                    zip_result = subprocess.run(
                        cmd_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                    if zip_result.returncode != 0:
                        await message.reply(f"❌ Error al comprimir {file_name}:\n{zip_result.stderr}")
                        continue

                    os.remove(file_path)

                    archive_parts = sorted([
                        f for f in os.listdir(output_dir)
                        if f.startswith(f"{file_name}_archive.7z")
                    ])
                    for part in archive_parts:
                        part_path = os.path.join(output_dir, part)
                        await client.send_document(chat_id, document=part_path)
                        os.remove(part_path)

                else:
                    await client.send_document(chat_id, document=file_path)
                    os.remove(file_path)

            await message.reply("✅ Archivos enviados correctamente.")

        except Exception as e:
            await message.reply(f"❌ Error inesperado: {str(e)}")


    elif command == "/hito":
        if cmd("htools", int_lvl):
            parts = text.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].startswith("https://"):
                await message.reply("Debes colocar un enlace válido después de /hito")
                return

            link_hitomi = parts[1].strip()
            await message.reply("Procesando enlace de Hitomi.la...")

            try:
                path_cbz = descargar_y_comprimir_hitomi(link_hitomi)
                await safe_call(
                    client.send_document,
                    chat_id=message.chat.id,
                    document=path_cbz,
                    protect_content=protect_content
                )
                os.remove(path_cbz)
            except Exception as e:
                await message.reply(f"Error al procesar el enlace: {e}")
                

    elif command == "/imgchest":
        if cmd("imgtools", int_lvl):
            reply = message.reply_to_message
            if reply and (reply.photo or reply.document or reply.video):
                await asyncio.create_task(create_imgchest_post(client, message))
            else:
                await message.reply("Por favor, usa el comando respondiendo a una foto.")
        return

    elif command in ("/compress", "/split", "/setsize", "/rename", "/caption"):
        if cmd("filetools", int_lvl):
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
    elif command in ("/setmail", "/sendmail", "/sendmailb", "/verify", "/setmb", "/setdelay", "/multisetmail", "/multisendmail", "/savemail", "/mailcopy"):
        if cmd("mailtools", int_lvl):
            parts = text.split()
            arg = parts[1] if len(parts) > 1 else ""
            repeats = min(int(arg), 99999) if arg.isdigit() else 1

            if command == "/setmail":
                await asyncio.create_task(set_mail(client, message, int_lvl))

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
        if cmd("filetools", int_lvl):
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
        if cmd("videotools", int_lvl):
            parts = text.split(maxsplit=1)
            arg = parts[1] if len(parts) > 1 else ""

            if command == "/convert":
                reply = message.reply_to_message
                if reply and (reply.video or (reply.document and reply.document.mime_type.startswith("video/"))):
                    await asyncio.create_task(compress_video(client, message, protect_content, int_lvl))

            elif command == "/autoconvert":
                auto_users[user_id] = not auto_users.get(user_id, False)
                status = "✅ Modo automático activado." if auto_users[user_id] else "🛑 Modo automático desactivado."
                await client.send_message(chat_id=message.chat.id, text=status, protect_content=False)

            elif command == "/calidad":
                await asyncio.create_task(update_video_settings(client, message, protect_content))

            elif command == "/cancel":
                try:
                    task_id = arg.strip()
                    await cancelar_tarea(int_lvl, client, task_id, message.chat.id, message, protect_content)
                except IndexError:
                    await client.send_message(
                        chat_id=message.chat.id,
                        text="⚠️ Debes proporcionar un ID válido para cancelar la tarea. Ejemplo: `/cancel <ID>`",
                        protect_content=True
                    )

            elif command == "/miniatura" or (message.photo and message.caption and message.caption.startswith("/miniatura")):
                await cambiar_miniatura(client, message)

            elif command == "/list":
                if int_lvl >= 3:
                    await listar_tareas(client, chat_id, protect_content, message, int_lvl)
                else:
                    await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para usar este comando.")

            elif auto and (message.video or (message.document and message.document.mime_type.startswith("video/"))):
                await asyncio.create_task(compress_video(client, message, protect_content, int_lvl))
        return

    elif command in ("/upfile", "/clearfiles", "/listfiles", "/sendfile"):
        if cmd("filetolink", int_lvl):
            reply = message.reply_to_message

            if command == "/upfile":
                await handle_up_command(client, message)

            elif command == "/clearfiles":
                await clear_vault_files(client, message)

            elif command == "/listfiles":
                await list_vault_files(client, message)

            elif command == "/sendfile":
                await send_vault_file_by_index(client, message)
                

    elif command in ("/scan", "/multiscan", "/resumecodes", "/resumetxtcodes", "/codesplit"):
        if cmd("webtools", int_lvl):
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
                    await message.reply("No se encontraron códigos válidos en el archivo.")
                os.remove(file_path)

    elif command == "/settings" and message.chat.type in (ChatType.PRIVATE, ChatType.BOT):
        args = textori.split()[1:]

        if not args:
            if is_owner:
                await send_setting_editor(client, message)
            else:
                return
            return

        if args[0] == "web":
            if not is_admin:
                return

            if len(args) >= 2 and args[1].lower() == "reload":
                from command.db.db import descargar_web_config

                descargar_web_config()
                await message.reply("🔄 Archivo 'web_access.json' recargado desde GitHub")
                return

            if len(args) >= 3:
                from command.db.db import guardar_datos_web

                usuario = args[1]
                contraseña = args[2]
                guardar_datos_web(user_id, usuario, contraseña)
                await message.reply("✅ Datos web guardados correctamente en 'web_access.json'")
            else:
                await message.reply("⚠️ Uso incorrecto. Formato esperado: /settings web <usuario> <contraseña>")
            return

        if not is_owner:
            return

        if args[0] == "copy" and len(args) >= 2:
            from command.db.db import descargar_web_config, descargar_bot_config
            from command.db.db import subir_bot_config

            bot_id = args[1]
            descargar_web_config()
            descargar_bot_config(bot_id)
            bot_info = await client.get_me()
            me_bot_id = str(bot_info.id)
            subir_bot_config(me_bot_id)
            await message.reply(f"📥 Configuración del bot {bot_id} copiada correctamente")
            return

        if "imgapi" in args:
            idx = args.index("imgapi")
            if len(args) > idx + 1:
                valor = args[idx + 1]
                guardar_parametro("imgapi", valor)
                await message.reply(f"✅ API de imágenes guardada como 'imgapi': '{valor}'")
            else:
                await message.reply("⚠️ Falta el valor para 'imgapi'")
            return

        if args[0] == "mail" and len(args) >= 4:
            from command.db.db import guardar_datos_correo

            correo = args[1]
            contraseña = args[2]
            servidor = " ".join(args[3:])
            guardar_datos_correo(correo, contraseña, servidor)
            await message.reply("✅ Datos de correo guardados correctamente en 'maildata.txt'")
            return
        elif args[0] == "mail":
            await message.reply("⚠️ Uso incorrecto. Formato esperado: /settings mail <correo> <contraseña> <servidor>")
            return

        if "public" in args:
            await send_setting_public(client, message)
        elif "protect" in args:
            await send_setting_protect(client, message)
        else:
            await send_setting_editor(client, message)
        return


    elif command == "/edituser" and message.chat.type in (ChatType.PRIVATE, ChatType.BOT):
        await send_access_editor(client, message)
        return
