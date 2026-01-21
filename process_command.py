import os
import asyncio
import re
import sqlite3
import subprocess
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatType

BASE_DIR = "vault_files/torrent_dl"

def is_bot_protect():
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
auto_files_users = {}
auto_users = {}

def cmd(command_env, int_lvl):
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

async def send_thanks_response(client, message):
    sticker1 = "CAACAgIAAxkBAAKIrWkAAccNDNiK8WZB5cO_sZz-wmlP2AAC3EsAAh9SSEtUr8U_tAoCoB4E"
    sticker2 = "CAACAgIAAxkBAAKIsWkAAcdpr_2KQcWqauJ3Gxs2Q8RqZwACkEMAAjeJSUu0N9e8-UNkeh4E"
    
    await client.send_sticker(chat_id=message.chat.id, sticker=sticker1)
    await asyncio.sleep(1)
    await message.reply("Esto... soy un bot, solo hago lo que estoy programando para hacer, no necesitas agradecerme")
    await asyncio.sleep(1)
    await message.reply("Pero mi creador @nakigeplayer se siente feliz de que consideres la idea de agradecer al bot")
    await asyncio.sleep(1)
    await client.send_sticker(chat_id=message.chat.id, sticker=sticker2)
async def process_command(client, message, user_id, username, chat_id, int_lvl, bot_manager=None):
    bot_info = await client.get_me()
    me_bot_id = str(bot_info.id)
    
    textori = message.text.strip() if message.text else ""

    if user_id is not None and str(user_id) == me_bot_id and textori.startswith('/'):
        return
    
    if user_id is not None and str(user_id) == me_bot_id and textori.startswith('.'):
        textori = textori.replace('.', '/', 1)
    
    text = textori.lower()
    if "gracias" in text:
        await send_thanks_response(client, message)

    is_anonymous = message.from_user is None

    protect_content = int_lvl < 3
    if not is_bot_protect() and protect_content:
        protect_content = False

    command = text.split()[0]

    if command == "/start":
        from command.admintools import handle_start
        await asyncio.create_task(handle_start(client, message))
    
    elif command == "/clone":
        if int_lvl == 6:
            if not bot_manager:
                await message.reply("Bot manager no disponible.")
                return
                
            parts = text.strip().split(maxsplit=1)
            if len(parts) < 2:
                await message.reply("Debes proporcionar un token.")
                return
            
            token = parts[1].strip()
            
            try:
                if ":" not in token:
                    await message.reply("Token inválido.")
                    return
                
                msg = await message.reply("Conectando bot...")
                
                new_bot = await bot_manager.clone_bot(token)
                
                if new_bot:
                    bot_info = await new_bot.app.get_me()
                    await msg.edit(f"✅ Bot creado: @{bot_info.username}")
                else:
                    await msg.edit("❌ Error al conectar el bot")
                    
            except Exception as e:
                error_msg = str(e)
                await message.reply(f"Error: {error_msg}")
        return
        
    elif command == "/where":
        user_id_str = str(message.from_user.id) if message.from_user else "No disponible"
        chat_id_str = str(message.chat.id) if message.chat else "No disponible"

        await message.reply(
            f"User: {user_id_str}\nChat: {chat_id_str}",
            quote=True
        )
        
    elif command == "/mydata":
        from command.mailtools.set_values import mydata
        await asyncio.create_task(mydata(client, message))

    elif command == "/help":
        from command.help import handle_help
        await asyncio.create_task(handle_help(client, message))

    elif command in ("/magnet", "/nyaa", "/nyaa18", "/sethumb"):
        if command == "/magnet":
            if cmd("torrent", int_lvl):
                from command.torrets_tools import process_magnet_download_telegram
                reply = message.reply_to_message
                parts = text.strip().split(maxsplit=2)

                link = None
                use_compression = False

                if reply and (reply.text or reply.caption):
                    text_reply = reply.text or reply.caption
                    magnet_match = re.search(r'magnet:\?[^\s]+', text_reply)
                    torrent_match = re.search(r'https?://[^\s]+\.torrent', text_reply)
                    if magnet_match:
                        link = magnet_match.group(0)
                    elif torrent_match:
                        link = torrent_match.group(0)

                if not link:
                    if len(parts) < 2:
                        await message.reply("❗ Debes proporcionar un enlace magnet o .torrent.")
                        return

                    if parts[1] == "-z":
                        use_compression = True
                        if len(parts) < 3:
                            await message.reply("❗ Debes proporcionar un enlace después de -z.")
                            return
                        arg_text = parts[2]
                    else:
                        arg_text = parts[1]

                    magnet_match = re.search(r'magnet:\?[^\s]+', arg_text)
                    torrent_match = re.search(r'https?://[^\s]+\.torrent', arg_text)

                    if magnet_match:
                        link = magnet_match.group(0)
                    elif torrent_match:
                        link = torrent_match.group(0)
                    else:
                        await message.reply("❗ El enlace debe ser un magnet o un archivo .torrent.")
                        return

                await process_magnet_download_telegram(client, message, link, use_compression)

        elif command == "/sethumb":
            if int_lvl >= 4:
                reply = message.reply_to_message
                if reply and (reply.photo or (reply.document and reply.document.mime_type.startswith("image/"))):
                    
                    thumb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thumb.jpg")
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)

                    
                    new_thumb_path = await client.download_media(reply, file_name=thumb_path)
                    if new_thumb_path:
                        await message.reply("✅ Miniatura actualizada correctamente.")
                    else:
                        await message.reply("❌ Error al descargar la miniatura.")
                else:
                    await message.reply("❗ Responde a una foto o archivo de imagen para establecer como miniatura.")

        elif command == "/nyaa":
            if cmd("torrent", int_lvl):
                parts = text.strip().split(maxsplit=1)
                if len(parts) < 2:
                    await message.reply("❗ Debes proporcionar un término de búsqueda después de /nyaa.")
                    return

                search_query = parts[1]
                from command.torrets_tools import search_in_nyaa
                await search_in_nyaa(client, message, search_query)

        elif command == "/nyaa18":
            if cmd("torrent", int_lvl):
                parts = text.strip().split(maxsplit=1)
                if len(parts) < 2:
                    await message.reply("❗ Debes proporcionar un término de búsqueda después de /nyaa18.")
                    return

                search_query = parts[1]
                from command.torrets_tools import search_in_sukebei
                await search_in_sukebei(client, message, search_query)

    
    elif command in ("/searchnh", "/search3h", "/nh", "/3h", "/cover3h", "/covernh", "/setfile", "/nhtxt", "/3htxt", "/dltxt", "/hito"):
        if cmd("htools", int_lvl):
            from command.htools import nh_combined_operation, nh_combined_operation_txt, cambiar_default_selection
            reply = message.reply_to_message
            parts = text.split(maxsplit=1)
            arg_text = parts[1] if len(parts) > 1 else ""

            if command == "/hito":
                if len(parts) < 2 or not parts[1].startswith("https://"):
                    await message.reply("Debes colocar un enlace válido después de /hito")
                    return
                link_hitomi = parts[1].strip()
                processing_msg = await message.reply("Procesando enlace de Hitomi.la...")
                try:
                    from command.get_files.hitomi import descargar_y_comprimir_hitomi
                    path_cbz = descargar_y_comprimir_hitomi(link_hitomi)
                    await processing_msg.delete()
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=path_cbz,
                        reply_to_message_id=message.id,
                        protect_content=protect_content
                    )
                    os.remove(path_cbz)
                except Exception as e:
                    await processing_msg.delete()
                    await message.reply(f"Error al procesar el enlace: {e}")
                return

            if command == "/setfile":
                new_selection = arg_text.strip().lower()
                valid_options = ["none", "cbz", "pdf", "both", "pics"]
                if new_selection in valid_options:
                    selection = None if new_selection == "none" else new_selection.upper()
                    cambiar_default_selection(user_id, selection)
                    await message.reply(f"¡Selección predeterminada cambiada a '{selection if selection else 'None'}'!")
                else:
                    await message.reply("Opción inválida. Usa: '/setfile cbz', '/setfile pdf', '/setfile both', '/setfile pics' o '/setfile none'.")
                return

            if command == "/searchnh":
                query = arg_text
                from command.htools import send_nhentai_results
                await send_nhentai_results(message, client, query)

            elif command == "/search3h":
                query = arg_text
                from command.htools import send_3hentai_results
                await send_3hentai_results(message, client, query)
                

            codes = arg_text.split(',') if ',' in arg_text else [arg_text] if arg_text else []
            codes_limpiados = [
                re.sub(r"https://nhentai\.net|https://[a-z]{2}\.3hentai\.net|https://3hentai\.net|/d/|/g/|/", "", code).strip()
                for code in codes
            ]
            
            if codes_limpiados != codes:
                codes = codes_limpiados
                warning_msg = await message.reply("Solo son necesarios los números pero ok")
                await asyncio.sleep(5)
                await warning_msg.delete()

            if command == "/nh":
                await asyncio.create_task(nh_combined_operation(client, message, codes, "nh", protect_content, user_id, "download", int_lvl))
            elif command == "/3h":
                await asyncio.create_task(nh_combined_operation(client, message, codes, "3h", protect_content, user_id, "download", int_lvl))
            elif command == "/cover3h":
                await asyncio.create_task(nh_combined_operation(client, message, codes, "3h", protect_content, user_id, "cover", int_lvl))
            elif command == "/covernh":
                await asyncio.create_task(nh_combined_operation(client, message, codes, "nh", protect_content, user_id, "cover", int_lvl))
            elif command == "/nhtxt":
                await asyncio.create_task(nh_combined_operation_txt(client, message, "nh", protect_content, user_id, "download", int_lvl))
            elif command == "/3htxt":
                await asyncio.create_task(nh_combined_operation_txt(client, message, "3h", protect_content, user_id, "download", int_lvl))
            elif command == "/dltxt" and reply and reply.document:
                from command.get_files.txt_a_cbz import txt_a_cbz
                path_txt = await client.download_media(reply.document)
                if not path_txt or not path_txt.endswith(".txt"):
                    if path_txt:
                        os.remove(path_txt)
                    await message.reply("Solo usar con archivos .txt")
                    return
                path_cbz = txt_a_cbz(path_txt)
                await client.send_document(chat_id=message.chat.id, document=path_cbz)

    elif command == "/megadl":
        if not cmd("download", int_lvl):
            return

        from command.down_tools import handle_megadl_command
        await handle_megadl_command(client, message, textori, chat_id)
        
    elif command in ("/compress", "/split", "/setsize", "/rename", "/caption"):
        if cmd("filetools", int_lvl):
            from command.filetools import handle_compress, set_size, rename, caption
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
                await caption(client, message.chat.id, file_id, caption_text, message)

    elif command in ("/setmail", "/sendmail", "/sendmailb", "/verify", "/setmb", "/setdelay", "/multisetmail", "/multisendmail", "/savemail", "/mailcopy"):
        if cmd("mailtools", int_lvl):
            from command.mailtools.set_values import set_mail, verify_mail, set_mail_limit, set_mail_delay, multisetmail, copy_manager
            from command.mailtools.send import send_mail, multisendmail
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
                respuesta = await copy_manager(user_id)
                await message.reply(respuesta)

    elif command in ("/id", "/sendid"):
        from command.telegramtools import get_file_id, send_file_by_id
        if command == "/id":
            await asyncio.create_task(get_file_id(client, message))
        elif command == "/sendid":
            await asyncio.create_task(send_file_by_id(client, message))

    elif command in ("/convert", "/calidad", "/autoconvert", "/cancel", "/list", "/miniatura"):
        if cmd("videotools", int_lvl):
            from command.videotools import compress_video, update_video_settings, cancelar_tarea, listar_tareas, cambiar_miniatura
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
                except Exception as e:
                    await message.reply(f"Error al cancelar tarea: {e}")
            elif command == "/miniatura":
                await cambiar_miniatura(client, message)
            elif command == "/list":
                if int_lvl >= 3:
                    await listar_tareas(client, chat_id, protect_content, message, int_lvl)
                else:
                    await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para usar este comando.")

    elif message.video or (message.document and message.document.mime_type and message.document.mime_type.startswith("video/")):
        if cmd("videotools", int_lvl) and auto_users.get(user_id, False):
            from command.videotools import compress_video
            await asyncio.create_task(compress_video(client, message, protect_content, int_lvl))

    elif message.photo and message.caption and message.caption.startswith("/miniatura"):
        if cmd("videotools", int_lvl):
            from command.videotools import cambiar_miniatura
            reply = message.reply_to_message
            if reply and (reply.video or (reply.document and reply.document.mime_type.startswith("video/"))):
                await cambiar_miniatura(client, message, reply)


    elif command in ("/upfile", "/clearfiles", "/listfiles", "/sendfile", "/autoup", "/cd", "/upwith"):
        if cmd("filetolink", int_lvl):
            from command.filetolink import (
                handle_up_command,
                clear_vault_files,
                list_vault_files,
                send_vault_file_by_index,
                handle_auto_up_command,
                handle_cd_command,
                handle_upwith_command
            )
            if command == "/upfile":
                await handle_up_command(client, message)
            elif command == "/clearfiles":
                await clear_vault_files(client, message)
            elif command == "/listfiles":
                await list_vault_files(client, message)
            elif command == "/sendfile":
                await send_vault_file_by_index(client, message)
            elif command == "/autoup":
                auto_files_users[user_id] = not auto_files_users.get(user_id, False)
                status = "✅ Auto-upload activado." if auto_files_users[user_id] else "🛑 Auto-upload desactivado."
                await client.send_message(chat_id=message.chat.id, text=status, protect_content=False)
            elif command == "/cd":
                await handle_cd_command(client, message)
            elif command == "/upwith":
                await handle_upwith_command(client, message)

    elif (message.document or message.video or message.audio or message.voice or message.photo or message.animation) and auto_files_users.get(user_id, False):
        if cmd("filetolink", int_lvl):
            from command.filetolink import handle_auto_up_command
            await asyncio.create_task(handle_auto_up_command(client, message))

    elif command in ("/scan", "/multiscan", "/resumecodes", "/resumetxtcodes", "/codesplit"):
        if cmd("webtools", int_lvl):
            from command.webtools import handle_scan, handle_multiscan, summarize_lines, split_codes
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

    elif command == "/q":
        if int_lvl >= 4: 
            from command.quotly import create_quote
            await asyncio.create_task(create_quote(client, message))
        else:
            await message.reply("⚠️ Este comando solo está disponible para la administración del bot")

    elif command == "/settings" and message.chat.type in (ChatType.PRIVATE, ChatType.BOT):
        from command.admintools import send_setting_editor, send_setting_protect, send_setting_public, guardar_parametro
        args = textori.split()[1:]
        if not args:
            if int_lvl == 6:
                await send_setting_editor(client, message)
            return
        if args[0] == "web":
            if int_lvl < 5:
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
        if int_lvl != 6:
            return
        if args[0] == "copy" and len(args) >= 2:
            from command.db.db import descargar_web_config, descargar_bot_config, subir_bot_config
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

    elif command == "/edituser" and message.chat.type in (ChatType.PRIVATE, ChatType.BOT):
        from command.admintools import send_access_editor
        await send_access_editor(client, message)

    elif command in ("/imgchest", "/imgup"):
        if cmd("imgtools", int_lvl):
            if not message.reply_to_message:
                await message.reply("❌ **Use el comando respondiendo a una imagen o archivo de imagen**")
                return
            
            reply = message.reply_to_message
            if not (reply.photo or (reply.document and reply.document.mime_type and 
                     reply.document.mime_type.startswith("image/"))):
                await message.reply("❌ **Debes responder a una imagen o archivo de imagen**")
                return
            
            try:
                from command.imgtools import create_imgchest_post
                await create_imgchest_post(client, message)
            except ImportError:
                await handle_imgchest_inline(client, message)
        else:
            await message.reply("⚠️ No tienes permiso para usar este comando.")
                    

    elif command == "/manga":
        if cmd("manga", int_lvl):
            from command.mangatools import handle_manga_search
            await handle_manga_search(client, message, textori)
