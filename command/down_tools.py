import os
import subprocess
import asyncio
import time
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

async def handle_megadl_command(client: Client, message: Message, mega_url: str, chat_id: int):
    desmega_path = os.path.join("command", "desmega")
    output_dir = os.path.join("vault_files", "mega_dl")
    os.makedirs(output_dir, exist_ok=True)

    progress_msg = await safe_call(client.send_message, chat_id, "📥 Iniciando descarga desde MEGA...")
    start_time = time.time()

    try:
        result = subprocess.run(
            [desmega_path, mega_url, "--path", output_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            await safe_call(progress_msg.edit_text, "❌ Error en la descarga MEGA")
            await safe_call(message.reply, f"❌ Error al ejecutar desmega:\n{result.stderr}")
            return

        files = os.listdir(output_dir)
        if not files:
            await safe_call(progress_msg.edit_text, "⚠️ No se encontraron archivos descargados")
            return

        total_files = len(files)
        sent_count = 0
        total_mb = sum(os.path.getsize(os.path.join(output_dir, f)) for f in files) / (1024 * 1024)
        sent_mb = 0
        current_file_name = ""
        current_mb_sent = 0

        def upload_progress(current, total):
            nonlocal current_mb_sent
            current_mb_sent = current / (1024 * 1024)

        await safe_call(progress_msg.edit_text, "📤 Preparando envío de archivos...")

        async def update_progress():
            while sent_count < total_files:
                elapsed = int(time.time() - start_time)
                formatted_time = format_time(elapsed)
                estimated_ratio = (sent_mb + current_mb_sent) / total_mb if total_mb > 0 else 0
                
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

        progress_task = asyncio.create_task(update_progress())

        try:
            seven_zip_exe = os.path.join("7z", "7zz")

            for file_name in files:
                file_path = os.path.join(output_dir, file_name)
                if not os.path.isfile(file_path):
                    continue

                current_file_name = file_name
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                current_mb_sent = 0

                if file_size_mb > 2000:
                    await safe_call(progress_msg.edit_text, f"📦 Comprimiendo {file_name}...")
                    
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
                        await safe_call(message.reply, f"❌ Error al comprimir {file_name}:\n{zip_result.stderr}")
                        continue

                    os.remove(file_path)

                    archive_parts = sorted([
                        f for f in os.listdir(output_dir)
                        if f.startswith(f"{file_name}_archive.7z")
                    ])

                    for part in archive_parts:
                        part_path = os.path.join(output_dir, part)
                        current_file_name = part
                        current_mb_sent = 0
                        part_size = os.path.getsize(part_path) / (1024 * 1024)
                        
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, chat_id, document=part_path, progress=upload_progress)
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                        
                        sent_mb += part_size
                        sent_count += 1
                        os.remove(part_path)

                else:
                    await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                    await safe_call(client.send_document, chat_id, document=file_path, progress=upload_progress)
                    await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                    
                    sent_mb += file_size_mb
                    sent_count += 1
                    os.remove(file_path)

        finally:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

        await safe_call(progress_msg.edit_text, "✅ Todos los archivos han sido enviados.")
        await asyncio.sleep(3)
        await safe_call(progress_msg.delete)

    except Exception as e:
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass
        await safe_call(progress_msg.edit_text, f"❌ Error inesperado: {str(e)}")
        await asyncio.sleep(5)
        await safe_call(progress_msg.delete)
