import os
import subprocess
import asyncio
import time
from datetime import datetime
import pytz
import re
from pyrogram import Client, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

async def handle_megadl_command(client: Client, message: Message, textori: str, chat_id: int, forze_zip: bool = False):
    mega_links = re.findall(r'https://mega\.nz/[^\s]+', textori)
    
    if not mega_links:
        await message.reply("❌ No se encontraron enlaces válidos de MEGA.")
        return

    unique_links = []
    seen_links = set()
    
    for link in mega_links:
        if link not in seen_links:
            unique_links.append(link)
            seen_links.add(link)

    desmega_path = os.path.join(BASE_DIR, "command", "desmega")

    # 📂 Carpeta nombrada con timestamp
    habana_tz = pytz.timezone('America/Havana')
    timestamp_folder = datetime.now(habana_tz).strftime("%Y%m%d%H%M%S")
    output_dir = os.path.join(BASE_DIR, "vault_files", timestamp_folder)
    os.makedirs(output_dir, exist_ok=True)

    progress_msg = await safe_call(client.send_message, chat_id, f"📥 Iniciando {len(unique_links)} descargas desde MEGA...")
    start_time = time.time()

    total_files = len(unique_links)
    processed_files = 0

    async def update_progress():
        while processed_files < total_files:
            try:
                elapsed = int(time.time() - start_time)
                formatted_time = format_time(elapsed)
                
                progress_ratio = processed_files / total_files if total_files else 0
                bar_length = 20
                filled_length = int(bar_length * progress_ratio)
                bar = "█" * filled_length + "▒" * (bar_length - filled_length)
                
                await safe_call(progress_msg.edit_text,
                    f"📥 Descargando desde MEGA...\n"
                    f"🕒 Tiempo: {formatted_time}\n"
                    f"📁 Progreso: {processed_files}/{total_files}\n"
                    f"📊 [{bar}] {progress_ratio*100:.1f}%\n"
                    f"🔄 Descargas activas..."
                )
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Error en update_progress: {e}")
                await asyncio.sleep(5)

    updater_task = asyncio.create_task(update_progress())

    try:
        for i, mega_url in enumerate(unique_links):
            await safe_call(progress_msg.edit_text, 
                f"📥 Descargando enlace {i+1}/{len(unique_links)}...\n"
                f"🔗 {mega_url[:50]}..."
            )

            process = subprocess.Popen(
                [desmega_path, mega_url, "--path", output_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                await safe_call(message.reply, f"❌ Error al descargar enlace {i+1}:\n{stderr}")
            else:
                processed_files += 1

        updater_task.cancel()
        try:
            await updater_task
        except asyncio.CancelledError:
            pass

        files = [f for f in os.listdir(output_dir) if not f.startswith('.megatmp')]
        if not files:
            await safe_call(progress_msg.edit_text, "⚠️ No se encontraron archivos descargados")
            return

        total_size = 0
        for root, dirs, files_in_dir in os.walk(output_dir):
            for file in files_in_dir:
                if not file.startswith('.megatmp'):
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)

        total_size_mb = total_size / (1024 * 1024)

        archive_name = f"{timestamp_folder}.7z"
        archive_path = os.path.join(output_dir, archive_name)
        seven_zip_exe = os.path.join(BASE_DIR, "7z", "7zz")

        if not os.path.exists(seven_zip_exe):
            await safe_call(progress_msg.edit_text, "❌ Error: No se encontró el ejecutable de 7zip")
            return

        # ⚖️ Nueva condición de compresión
        if total_size_mb > 2000 or forze_zip:
            await safe_call(progress_msg.edit_text, 
                f"📦 Creando archivo comprimido...\n"
                f"📊 Tamaño total: {total_size_mb:.2f} MB"
            )

            if total_size_mb > 2000:
                # Dividir en partes de 2000 MB
                cmd_args = [
                    seven_zip_exe,
                    'a',
                    '-mx=0',
                    f'-v2000m',
                    archive_path,
                    os.path.join(output_dir, '*')
                ]
            else:
                # Archivo único
                cmd_args = [
                    seven_zip_exe,
                    'a',
                    '-mx=0',
                    archive_path,
                    os.path.join(output_dir, '*')
                ]

            zip_result = subprocess.run(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=output_dir
            )

            if zip_result.returncode != 0:
                await safe_call(message.reply, f"❌ Error al comprimir archivos:\n{zip_result.stderr}")
                return

            # Enviar archivos comprimidos (partes o único)
            for file in sorted(os.listdir(output_dir)):
                if file.startswith(timestamp_folder) and file.endswith(".7z") or ".7z." in file:
                    part_path = os.path.join(output_dir, file)
                    await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                    await safe_call(client.send_document, chat_id, document=part_path)
                    await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                    os.remove(part_path)

        else:
            # 🚫 No se comprime, se envían los archivos directamente
            for root, dirs, files_in_dir in os.walk(output_dir):
                for file in files_in_dir:
                    if not file.startswith('.megatmp'):
                        file_path = os.path.join(root, file)
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, chat_id, document=file_path)
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                        os.remove(file_path)

        await safe_call(progress_msg.edit_text, "✅ Todos los archivos han sido enviados.")
        await asyncio.sleep(3)
        await safe_call(progress_msg.delete)

    except Exception as e:
        updater_task.cancel()
        try:
            await updater_task
        except asyncio.CancelledError:
            pass
        await safe_call(progress_msg.edit_text, f"❌ Error inesperado: {str(e)}")
        await asyncio.sleep(5)
        await safe_call(progress_msg.delete)
