import os
import subprocess
import asyncio
import time
from datetime import datetime
import pytz
from pyrogram import Client, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait

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

async def handle_megadl_command(client: Client, message: Message, textori: str, chat_id: int):
    if len(textori.split()) < 2:
        await message.reply("❌ Debes proporcionar al menos un enlace de MEGA.")
        return

    links = textori.split()[1:]
    unique_links = []
    seen_links = set()
    
    for link in links:
        if link.startswith("https://mega.nz/") and link not in seen_links:
            unique_links.append(link)
            seen_links.add(link)

    if not unique_links:
        await message.reply("❌ No se encontraron enlaces válidos de MEGA.")
        return

    desmega_path = os.path.join("command", "desmega")
    output_dir = os.path.join("vault_files", "mega_dl")
    os.makedirs(output_dir, exist_ok=True)

    progress_msg = await safe_call(client.send_message, chat_id, f"📥 Iniciando {len(unique_links)} descargas desde MEGA...")
    start_time = time.time()

    async def monitor_download():
        while True:
            try:
                temp_files = [f for f in os.listdir(output_dir) if '.megatmp' in f]
                if temp_files:
                    temp_file = os.path.join(output_dir, temp_files[0])
                    if os.path.exists(temp_file):
                        file_size = os.path.getsize(temp_file)
                        file_size_mb = file_size / (1024 * 1024)
                        elapsed = int(time.time() - start_time)
                        formatted_time = format_time(elapsed)
                        
                        await safe_call(progress_msg.edit_text,
                            f"📥 Descargando desde MEGA...\n"
                            f"📦 Tamaño descargado: {file_size_mb:.2f} MB\n"
                            f"⏱️ Tiempo: {formatted_time}\n"
                            f"🔄 Descargas activas..."
                        )
                else:
                    elapsed = int(time.time() - start_time)
                    formatted_time = format_time(elapsed)
                    await safe_call(progress_msg.edit_text,
                        f"📥 Procesando {len(unique_links)} enlaces MEGA...\n"
                        f"⏱️ Tiempo: {formatted_time}\n"
                        f"🔄 Iniciando descargas..."
                    )
                
                await asyncio.sleep(10)
            except Exception as e:
                print(f"Error en monitor_download: {e}")
                await asyncio.sleep(10)

    monitor_task = asyncio.create_task(monitor_download())

    try:
        for i, mega_url in enumerate(unique_links):
            await safe_call(progress_msg.edit_text, f"📥 Descargando enlace {i+1}/{len(unique_links)}...")

            process = subprocess.Popen(
                [desmega_path, mega_url, "--path", output_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                await safe_call(message.reply, f"❌ Error al descargar enlace {i+1}:\n{stderr}")

        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        files = [f for f in os.listdir(output_dir) if not f.startswith('.megatmp')]
        if not files:
            await safe_call(progress_msg.edit_text, "⚠️ No se encontraron archivos descargados")
            return

        habana_tz = pytz.timezone('America/Havana')
        timestamp = datetime.now(habana_tz).strftime("%Y_%m_%d_%H_%M")
        archive_name = f"Mega_dl_{timestamp}.7z"
        archive_path = os.path.join(output_dir, archive_name)
        seven_zip_exe = os.path.join("7z", "7zz")

        total_size = 0
        for root, dirs, files_in_dir in os.walk(output_dir):
            for file in files_in_dir:
                if not file.startswith('.megatmp'):
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)

        total_size_mb = total_size / (1024 * 1024)

        await safe_call(progress_msg.edit_text, f"📦 Creando archivo comprimido...")

        if total_size_mb > 2000:
            cmd_args = [
                seven_zip_exe,
                'a',
                '-mx=0',
                f'-v2000m',
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

            archive_parts = sorted([
                f for f in os.listdir(output_dir)
                if f.startswith(archive_name.replace('.7z', ''))
            ])

            sent_count = 0
            total_parts = len(archive_parts)

            for part in archive_parts:
                part_path = os.path.join(output_dir, part)
                part_size_mb = os.path.getsize(part_path) / (1024 * 1024)
                
                await safe_call(progress_msg.edit_text, f"📤 Enviando parte {sent_count+1}/{total_parts} ({part_size_mb:.2f} MB)...")
                
                await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                await safe_call(client.send_document, chat_id, document=part_path)
                await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                
                sent_count += 1
                os.remove(part_path)

        else:
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

            archive_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
            await safe_call(progress_msg.edit_text, f"📤 Enviando archivo ({archive_size_mb:.2f} MB)...")
            
            await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
            await safe_call(client.send_document, chat_id, document=archive_path)
            await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
            
            os.remove(archive_path)

        for root, dirs, files_in_dir in os.walk(output_dir, topdown=False):
            for file in files_in_dir:
                if not file.startswith('.megatmp'):
                    os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))

        await safe_call(progress_msg.edit_text, "✅ Todos los archivos han sido enviados.")
        await asyncio.sleep(3)
        await safe_call(progress_msg.delete)

    except Exception as e:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        await safe_call(progress_msg.edit_text, f"❌ Error inesperado: {str(e)}")
        await asyncio.sleep(5)
        await safe_call(progress_msg.delete)
