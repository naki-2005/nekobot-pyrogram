import os
import re
import shutil
import subprocess
import asyncio
import mimetypes
import time
from datetime import datetime
from pyrogram import Client, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
thumb = os.path.join(parent_dir, "thumb.jpg")

VAULT_FOLDER = "vault_files"
SEVEN_ZIP_EXE = os.path.join("7z", "7zz")
MAX_SIZE_MB = 2000

user_cd_paths = {}
user_upwith_filters = {}
user_upwith_counters = {}

def parse_nested_indices(text):
    result = []
    for part in text.split(","):
        part = part.strip()
        if part == "*":
            result.append("ALL")
        elif part.isdigit():
            result.append(int(part))
    return result

def get_info(msg: Message):
    media = next((m for m in [msg.document, msg.photo, msg.audio, msg.video, msg.voice, msg.animation, msg.sticker] if m), None)
    fname = getattr(media, "file_name", None) or media.file_id if media else None
    fid = media.file_id if media else None
    size = getattr(media, "file_size", 0) / (1024 * 1024) if media else 0.0
    return fname, fid, size

def secure_filename(fname: str) -> str:
    fname = os.path.basename(fname)
    fname = re.sub(r"[^a-zA-Z0-9_.\- ]", "", fname)
    return fname or "file"

def get_all_vault_files():
    all_files = []
    for root, _, files in os.walk(VAULT_FOLDER):
        rel_root = os.path.relpath(root, VAULT_FOLDER)
        rel_root = "" if rel_root == "." else rel_root
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            all_files.append((rel_root, fname, fpath))
    return all_files

async def clear_vault_files(client: Client, message: Message):
    if not os.path.isdir(VAULT_FOLDER):
        await message.reply("📁 La carpeta no existe.")
        return
    try:
        shutil.rmtree(VAULT_FOLDER)
        os.makedirs(VAULT_FOLDER, exist_ok=True)
        await message.reply("✅ Todos los archivos y carpetas fueron eliminados.")
    except Exception as e:
        await message.reply(f"❌ Error al borrar: {e}")

async def handle_up_command(client: Client, message: Message):
    from arg_parser import get_args
    args = get_args()

    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("❌ Este comando debe responder a un archivo.")
        return

    fname, fid, size_mb = get_info(message.reply_to_message)
    parts = message.text.strip().split(maxsplit=1)
    
    user_id = message.from_user.id
    
    if user_id in user_upwith_filters:
        pattern_info = user_upwith_filters[user_id]
        current_counter = user_upwith_counters.get(user_id, pattern_info["start"])
        
        if current_counter <= pattern_info["end"]:
            num_str = str(current_counter).zfill(pattern_info["zeros"])
            filename = pattern_info["pattern"].replace("{num}", num_str) + pattern_info["extension"]
            user_upwith_counters[user_id] = current_counter + 1
            
            if user_upwith_counters[user_id] > pattern_info["end"]:
                await message.reply("Todos los nombres en el filtro han sido utilizados, restaurando comportamiento natural de /upfile")
                del user_upwith_filters[user_id]
                del user_upwith_counters[user_id]
        else:
            filename = fname or "archivo"
    else:
        raw_path = parts[1].strip() if len(parts) == 2 else fname or "archivo"
        filename = raw_path
    
    if user_id in user_cd_paths:
        cd_path = user_cd_paths[user_id]
        if cd_path:
            safe_parts = [secure_filename(p) for p in cd_path.split("/")]
            relative_path = os.path.join(*safe_parts, filename)
        else:
            safe_parts = [secure_filename(p) for p in filename.split("/")]
            relative_path = os.path.join(*safe_parts)
    else:
        safe_parts = [secure_filename(p) for p in filename.split("/")]
        relative_path = os.path.join(*safe_parts)
    
    full_path = os.path.join(VAULT_FOLDER, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    progress_msg = await message.reply("📥 Iniciando descarga...")
    start_time = time.time()
    download_completed = False
    current_bytes = 0
    total_bytes = 0

    async def update_download_progress():
        last_update = time.time()
        while not download_completed:
            if total_bytes > 0:
                elapsed = int(time.time() - start_time)
                formatted_time = format_time(elapsed)
                progress_ratio = current_bytes / total_bytes
                bar_length = 20
                filled_length = int(bar_length * progress_ratio)
                bar = "█" * filled_length + "▒" * (bar_length - filled_length)
                current_mb = current_bytes / (1024 * 1024)
                total_mb = total_bytes / (1024 * 1024)

                if time.time() - last_update >= 10:
                    await safe_call(progress_msg.edit_text,
                        f"📥 Descargando archivo...\n"
                        f"🕒 Tiempo: {formatted_time}\n"
                        f"📊 Progreso: {current_mb:.2f} MB / {total_mb:.2f} MB\n"
                        f"📉 [{bar}] {progress_ratio*100:.1f}%\n"
                        f"📄 Archivo: {os.path.basename(full_path)}"
                    )
                    last_update = time.time()
            await asyncio.sleep(0.5)

    def download_progress(current, total):
        nonlocal current_bytes, total_bytes
        current_bytes = current
        total_bytes = total

    download_task = asyncio.create_task(update_download_progress())

    try:
        await client.download_media(message.reply_to_message, full_path, progress=download_progress)
        download_completed = True
        await download_task
        elapsed = int(time.time() - start_time)
        await progress_msg.delete()
    except Exception as e:
        download_completed = True
        await download_task
        await progress_msg.edit_text(f"❌ Error en descarga: {e}")
        return

    if args.web:
        download_link = f"{args.web.rstrip('/')}/{relative_path.replace(os.sep, '/')}"
        await message.reply(f"✅ Descarga completada en {elapsed}s\n🔗 Link: `{download_link}`")
    else:
        await message.reply(f"✅ Descarga completada en {elapsed}s\nArchivo guardado como `{relative_path}`")

async def handle_cd_command(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) == 1:
        user_cd_paths[user_id] = ""
        await message.reply("📁 Ruta restablecida a la raíz de vault_files")
        return
    
    new_path = parts[1].strip()
    safe_parts = [secure_filename(p) for p in new_path.split("/")]
    final_path = "/".join(safe_parts)
    
    user_cd_paths[user_id] = final_path
    await message.reply(f"📁 Ruta cambiada a: `{final_path}`")

async def handle_upwith_command(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await message.reply("❌ Uso: /upwith <patrón>")
        await message.reply("Ejemplo: /upwith Anime/{01-12}.mp4")
        await message.reply("Ejemplo: /upwith {1-24}.mkv")
        return
    
    pattern_text = parts[1].strip()
    
    match = re.search(r'\{(\d+)-(\d+)\}', pattern_text)
    if not match:
        await message.reply("❌ Patrón no válido. Debe contener {inicio-fin}")
        return
    
    start_num = int(match.group(1))
    end_num = int(match.group(2))
    
    if start_num > end_num:
        await message.reply("❌ El número inicial no puede ser mayor que el final")
        return
    
    zeros = len(match.group(1))
    pattern_before = pattern_text[:match.start()]
    pattern_after = pattern_text[match.end():]
    
    extension_match = re.search(r'\.\w+$', pattern_after)
    if extension_match:
        extension = extension_match.group(0)
        pattern_after = pattern_after[:extension_match.start()]
    else:
        extension = ""
    
    user_upwith_filters[user_id] = {
        "pattern": pattern_before + "{num}" + pattern_after,
        "start": start_num,
        "end": end_num,
        "zeros": zeros,
        "extension": extension
    }
    
    user_upwith_counters[user_id] = start_num
    
    await message.reply(f"✅ Filtro establecido: {start_num} a {end_num} archivos")
    await message.reply(f"📄 Patrón: `{pattern_before}{'0'*zeros}{pattern_after}{extension}`")

async def handle_auto_up_command(client: Client, message: Message):
    from arg_parser import get_args
    args = get_args()

    fname, fid, size_mb = get_info(message)
    user_id = message.from_user.id
    
    if user_id in user_cd_paths:
        cd_path = user_cd_paths[user_id]
        if cd_path:
            safe_parts = [secure_filename(p) for p in cd_path.split("/")]
            safe_parts.append(secure_filename(fname or "archivo"))
            relative_path = os.path.join(*safe_parts)
        else:
            safe_parts = [secure_filename(p) for p in (fname or "archivo").split("/")]
            relative_path = os.path.join(*safe_parts)
    else:
        safe_parts = [secure_filename(p) for p in (fname or "archivo").split("/")]
        relative_path = os.path.join(*safe_parts)
    
    full_path = os.path.join(VAULT_FOLDER, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    progress_msg = await message.reply("📥 Iniciando descarga automática...")
    start_time = time.time()
    download_completed = False
    current_bytes = 0
    total_bytes = 0

    async def update_download_progress():
        last_update = time.time()
        while not download_completed:
            if total_bytes > 0:
                elapsed = int(time.time() - start_time)
                formatted_time = format_time(elapsed)
                progress_ratio = current_bytes / total_bytes
                bar_length = 20
                filled_length = int(bar_length * progress_ratio)
                bar = "█" * filled_length + "▒" * (bar_length - filled_length)
                current_mb = current_bytes / (1024 * 1024)
                total_mb = total_bytes / (1024 * 1024)

                if time.time() - last_update >= 10:
                    await safe_call(progress_msg.edit_text,
                        f"📥 Descargando archivo...\n"
                        f"🕒 Tiempo: {formatted_time}\n"
                        f"📊 Progreso: {current_mb:.2f} MB / {total_mb:.2f} MB\n"
                        f"📉 [{bar}] {progress_ratio*100:.1f}%\n"
                        f"📄 Archivo: {os.path.basename(full_path)}"
                    )
                    last_update = time.time()
            await asyncio.sleep(0.5)

    def download_progress(current, total):
        nonlocal current_bytes, total_bytes
        current_bytes = current
        total_bytes = total

    download_task = asyncio.create_task(update_download_progress())

    try:
        await client.download_media(message, full_path, progress=download_progress)
        download_completed = True
        await download_task
        elapsed = int(time.time() - start_time)
        await progress_msg.delete()
    except Exception as e:
        download_completed = True
        await download_task
        await progress_msg.edit_text(f"❌ Error en descarga: {e}")
        return

    if args.web:
        download_link = f"{args.web.rstrip('/')}/{relative_path.replace(os.sep, '/')}"
        await message.reply(f"✅ Descarga automática completada en {elapsed}s\n🔗 Link: `{download_link}`")
    else:
        await message.reply(f"✅ Descarga automática completada en {elapsed}s\nArchivo guardado como `{relative_path}`")

async def list_vault_files(client: Client, message: Message):
    if not os.path.isdir(VAULT_FOLDER):
        await client.send_message(message.from_user.id, "📁 La carpeta está vacía o no existe.")
        return
    
    def natural_sort_key(s):
        if not isinstance(s, str):
            s = str(s)
        return [int(text) if text.isdigit() else text.lower() 
                for text in re.split(r'(\d+)', s)]
    
    def list_files_recursive(directory, base_path, prefix="", file_index_start=0):
        items = []
        file_count = file_index_start
        
        try:
            for name in sorted(os.listdir(directory), key=natural_sort_key):
                full_path = os.path.join(directory, name)
                rel_path = os.path.relpath(full_path, base_path)
                
                if os.path.isdir(full_path):
                    items.append(f"📁 {prefix}{name}/")
                    sub_items, file_count = list_files_recursive(full_path, base_path, prefix + "  ", file_count)
                    items.extend(sub_items)
                else:
                    file_count += 1
                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                    items.append(f"{file_count:4d}. 📄 {prefix}{name} — {size_mb:.2f} MB")
        
        except Exception:
            pass
        
        return items, file_count
    
    texto = "📄 Archivos disponibles:\n\n"
    all_items, total_files = list_files_recursive(VAULT_FOLDER, VAULT_FOLDER)
    
    current_chunk = ""
    chunks = []
    
    for item in all_items:
        if len(current_chunk) + len(item) + 1 < 2000:
            current_chunk += item + "\n"
        else:
            chunks.append(current_chunk)
            current_chunk = item + "\n"
    
    if current_chunk:
        chunks.append(current_chunk)
    
    for i, chunk in enumerate(chunks):
        if i == 0:
            header = f"📄 Archivos disponibles ({total_files} archivos):\n\n"
        else:
            header = f"📄 Continuación ({i+1}/{len(chunks)}):\n\n"
        
        await client.send_message(message.from_user.id, header + chunk)
        
async def safe_call(func, *args, **kwargs):
    while True:
        try:
            return await func(*args, **kwargs)
        except FloodWait as e:
            print(f"⏳ Esperando {e.value} seg para continuar")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"❌ Error inesperado en {func.__name__}: {type(e).__name__}: {e}")
            raise

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    else:
        return f"{s}s"

async def send_vault_file_by_index(client, message):
    text = message.text.strip()
    args = text.split()
    if len(args) < 2:
        await safe_call(client.send_message, message.chat.id, "❌ Debes especificar los índices")
        return

    mode = None
    delete_after = False
    custom_name = ""
    flags = [arg for arg in args if arg.startswith("-")]
    for flag in flags:
        if flag == "-z":
            mode = "auto_compress"
        elif flag == "-Z":
            mode = "named_compress"
        elif flag == "-d":
            delete_after = True
        elif flag == "-m":
            mode = "with_thumb"

    non_flags = [arg for arg in args if not arg.startswith("-")]
    index_str = non_flags[1] if len(non_flags) > 1 else non_flags[0]
    if mode == "named_compress" and len(non_flags) > 2:
        custom_name = " ".join(non_flags[2:])

    all_files = get_all_vault_files()
    selected_files = []

    for idx in parse_nested_indices(index_str):
        if idx == "ALL":
            selected_files = [f[2] for f in all_files]
            break
        elif isinstance(idx, int) and 1 <= idx <= len(all_files):
            selected_files.append(all_files[idx - 1][2])

    if not selected_files:
        await safe_call(client.send_message, message.chat.id, "❌ No se encontraron archivos válidos")
        return

    files_to_compress = []
    files_to_delete_after = []

    if mode in ["auto_compress", "named_compress"]:
        if mode == "named_compress" and not custom_name:
            await safe_call(client.send_message, message.chat.id, "❌ Debes especificar un nombre después de -Z")
            return

        compressing_msg = await safe_call(client.send_message, message.chat.id, "🗜️ Comprimiendo archivos...")

        try:
            if mode == "named_compress":
                archive_name = secure_filename(custom_name or "compressed")
                archive_path = os.path.join(VAULT_FOLDER, f"{archive_name}.7z")
                cmd_args = [SEVEN_ZIP_EXE, "a", "-mx=0", archive_path]
                cmd_args.extend(selected_files)
                subprocess.run(cmd_args, check=True, timeout=3600)
                files_to_compress = [archive_path]
                files_to_delete_after.append(archive_path)
                if delete_after:
                    files_to_delete_after.extend(selected_files)
            else:
                for path in selected_files:
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                    if size_mb > MAX_SIZE_MB or True:
                        base_name = os.path.splitext(os.path.basename(path))[0]
                        archive_path = os.path.join(VAULT_FOLDER, f"{base_name}.7z")
                        cmd_args = [SEVEN_ZIP_EXE, "a", "-mx=0", archive_path, path]
                        subprocess.run(cmd_args, check=True, timeout=3600)
                        files_to_compress.append(archive_path)
                        files_to_delete_after.append(archive_path)
                        if delete_after:
                            files_to_delete_after.append(path)
                    else:
                        files_to_compress.append(path)
                        if delete_after:
                            files_to_delete_after.append(path)

            await safe_call(compressing_msg.delete)

        except subprocess.TimeoutExpired:
            await safe_call(compressing_msg.edit_text, "❌ Timeout al comprimir")
            return
        except subprocess.CalledProcessError as e:
            await safe_call(compressing_msg.edit_text, f"❌ Error al comprimir: {e}")
            return
        except Exception as e:
            await safe_call(compressing_msg.edit_text, f"❌ Error inesperado: {e}")
            return
    else:
        files_to_compress = selected_files
        if delete_after:
            files_to_delete_after.extend(selected_files)

    progress_msg = await safe_call(client.send_message, message.chat.id, "📤 Iniciando envío de archivos...")
    start_time = time.time()
    total_files = len(files_to_compress)
    sent_count = 0
    total_mb = sum(os.path.getsize(p) for p in files_to_compress) / (1024 * 1024)
    sent_mb = 0
    current_file_name = ""
    current_mb_sent = 0

    async def update_progress():
        while sent_count < total_files:
            elapsed = int(time.time() - start_time)
            formatted_time = format_time(elapsed)
            estimated_ratio = (sent_mb + current_mb_sent) / total_mb if total_mb else 0
            bar_length = 20
            filled_length = int(bar_length * estimated_ratio)
            bar = "█" * filled_length + "▒" * (bar_length - filled_length)

            await safe_call(progress_msg.edit_text,
                f"📦 Enviando archivos...\n"
                f"🕒 Tiempo: {formatted_time}\n"
                f"📁 Archivos: {sent_count}/{total_files}\n"
                f"📊 Progreso: {sent_mb + current_mb_sent:.2f} MB / {total_mb:.2f} MB\n"
                f"📉 [{bar}] {estimated_ratio*100:.1f}%\n"
                f"📄 Archivo actual: {current_file_name}"
            )
            await asyncio.sleep(10)

    updater_task = asyncio.create_task(update_progress())

    try:
        for path in files_to_compress:
            try:
                size_mb = os.path.getsize(path) / (1024 * 1024)
                current_file_name = os.path.basename(path)
                current_mb_sent = 0

                def progress(current, total):
                    nonlocal current_mb_sent
                    current_mb_sent = current / (1024 * 1024)

                mime_type, _ = mimetypes.guess_type(path)
                mime_main = mime_type.split("/")[0] if mime_type else ""
                filename = os.path.basename(path)

                if size_mb > MAX_SIZE_MB and path.endswith('.7z'):
                    base_name = os.path.splitext(os.path.basename(path))[0]
                    archive_path = os.path.join(VAULT_FOLDER, f"{base_name}_split.7z")
                    cmd_args = [SEVEN_ZIP_EXE, "a", "-mx=0", f"-v{MAX_SIZE_MB}m", archive_path, path]
                    subprocess.run(cmd_args, check=True)

                    archive_base = os.path.splitext(archive_path)[0]
                    archive_parts = sorted([
                        f for f in os.listdir(VAULT_FOLDER)
                        if f.startswith(os.path.basename(archive_base)) and (f.endswith(".7z") or f.endswith(".7z.001"))
                    ])

                    for part in archive_parts:
                        part_path = os.path.join(VAULT_FOLDER, part)
                        part_size = os.path.getsize(part_path) / (1024 * 1024)
                        current_file_name = part
                        current_mb_sent = 0

                        await safe_call(client.send_chat_action, message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, message.chat.id, document=part_path, caption=f"📦 {part}", progress=progress, thumb=thumb)
                        await safe_call(client.send_chat_action, message.chat.id, enums.ChatAction.CANCEL)

                        sent_mb += part_size
                        files_to_delete_after.append(part_path)

                else:
                    await safe_call(client.send_chat_action, message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)

                    if mime_main == "image" and not filename.lower().endswith(".webp"):
                        await safe_call(client.send_photo, message.chat.id, photo=path, caption=f"🖼️ {os.path.basename(path)}", progress=progress)
                    else:
                        if mode == "with_thumb" and os.path.exists(thumb):
                            await safe_call(client.send_document, message.chat.id, document=path, caption=f"📤 {os.path.basename(path)}", progress=progress, thumb=thumb)
                        else:
                            await safe_call(client.send_document, message.chat.id, document=path, caption=f"📤 {os.path.basename(path)}", progress=progress)

                    await safe_call(client.send_chat_action, message.chat.id, enums.ChatAction.CANCEL)
                    sent_mb += size_mb

                sent_count += 1

            except Exception as e:
                await safe_call(client.send_message, message.chat.id, f"⚠️ Error al enviar `{os.path.basename(path)}`: {e}")

    finally:
        updater_task.cancel()
        try:
            await updater_task
        except asyncio.CancelledError:
            pass

        for file_path in files_to_delete_after:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"⚠️ Error al borrar {file_path}: {e}")

        await safe_call(progress_msg.delete)
        await safe_call(client.send_message, message.chat.id, "✅ Todos los archivos han sido enviados.")
