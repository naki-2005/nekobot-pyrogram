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

VAULT_FOLDER = "vault_files"
SEVEN_ZIP_EXE = os.path.join("7z", "7zz")
MAX_SIZE_MB = 2000

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
    raw_path = parts[1].strip() if len(parts) == 2 else fname or "archivo"
    safe_parts = [secure_filename(p) for p in raw_path.split("/")]
    relative_path = os.path.join(*safe_parts)
    full_path = os.path.join(VAULT_FOLDER, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    await client.download_media(message.reply_to_message, full_path)

    if args.web:
        download_link = f"{args.web.rstrip('/')}/{relative_path.replace(os.sep, '/')}"
        await message.reply(f"🔗 Link de descarga: {download_link}")
    else:
        await message.reply(f"✅ Archivo guardado como `{relative_path}` en `{VAULT_FOLDER}`.")

async def list_vault_files(client: Client, message: Message):
    if not os.path.isdir(VAULT_FOLDER):
        await client.send_message(message.from_user.id, "📁 La carpeta está vacía o no existe.")
        return

    texto = "📄 Archivos disponibles:\n\n"
    all_files = get_all_vault_files()

    for idx, (folder, fname, fpath) in enumerate(all_files, start=1):
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        ruta = folder if folder else "Root"
        texto += f"{idx}. {fname} — {size_mb:.2f} MB ({ruta})\n"

    await client.send_message(message.from_user.id, texto.strip())

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

async def send_video_with_thumbnail(client, chat_id, video_path, caption, progress_callback):
    import os
    import subprocess
    import random

    def get_video_duration(video_path):
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            duration = result.stdout.strip()
            if duration == 'N/A' or not duration:
                raise ValueError("No se pudo obtener la duración del video.")
            return int(float(duration))
        except Exception as e:
            print(f"Error al obtener la duración del video: {e}")
            return 0

    async def generate_thumbnail(video_path):
        try:
            video_duration = get_video_duration(video_path)
            if video_duration <= 0:
                raise ValueError("No se pudo determinar la duración del video.")

            fps = 24
            max_frames = min(video_duration * fps, 10000)
            random_frame = random.randint(0, int(max_frames) - 1)
            random_time = random_frame / fps

            output_thumb = f"{os.path.splitext(video_path)[0]}_miniatura.jpg"

            subprocess.run([
                "ffmpeg",
                "-i", video_path,
                "-ss", str(random_time),
                "-vframes", "1",
                output_thumb
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            if not os.path.exists(output_thumb):
                raise IOError("No se pudo generar la miniatura.")

            return output_thumb
        except Exception as e:
            print(f"Error al generar la miniatura: {e}")
            return None

    thumbnail = await generate_thumbnail(video_path)

    await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_VIDEO)
    await safe_call(client.send_video,
        chat_id,
        video=video_path,
        caption=caption,
        thumb=thumbnail if thumbnail else None,
        progress=progress_callback
    )
    await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)

    if thumbnail and os.path.exists(thumbnail):
        try:
            os.remove(thumbnail)
        except Exception as e:
            print(f"⚠️ Error al borrar miniatura: {e}")
            

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
                        await safe_call(client.send_document, message.chat.id, document=part_path, caption=f"📦 {part}", progress=progress)
                        await safe_call(client.send_chat_action, message.chat.id, enums.ChatAction.CANCEL)

                        sent_mb += part_size
                        files_to_delete_after.append(part_path)

                else:
                    await safe_call(client.send_chat_action, message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)

                    if mime_main == "image":
                        await safe_call(client.send_photo, message.chat.id, photo=path, caption=f"🖼️ {os.path.basename(path)}", progress=progress)
                    elif mime_main == "video":
                        await send_video_with_thumbnail(client, message.chat.id, path, f"🎬 {os.path.basename(path)}", progress)
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
