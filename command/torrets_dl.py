import os
import time
import datetime
import shutil
import libtorrent as lt
import asyncio
import subprocess
import aiohttp
import aiofiles
import threading
import re
import uuid
import requests
from pyrogram import enums
from pyrogram.errors import FloodWait, MessageIdInvalid

SEVEN_ZIP_EXE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "7z", "7zz")
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vault_files", "torrent_dl")
TEMP_DIR = os.path.join(BASE_DIR, "downloading")
active_downloads = {}
downloads_lock = threading.Lock()
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
thumb = os.path.join(parent_dir, "thumb.jpg")
def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def clean_filename(name):
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáéíóúÁÉÍÓÚ0123456789 ()[]"
    cleaned = ''.join(c for c in name if c in allowed_chars)
    return cleaned[:50] + '.7z' if len(cleaned) > 50 else cleaned + '.7z'

def start_session():
    ses = lt.session()
    ses.listen_on(6881, 6891)
    ses.start_dht()
    return ses

def add_torrent(ses, magnet_uri, save_path):
    params = {
        'save_path': save_path,
        'storage_mode': lt.storage_mode_t.storage_mode_sparse,
    }
    handle = lt.add_magnet_uri(ses, magnet_uri, params)
    handle.set_sequential_download(False)
    return handle

async def wait_for_metadata(handle):
    log("Descargando metadata...")
    while not handle.has_metadata():
        await asyncio.sleep(1)
    log("Metadata obtenida")

async def monitor_download(handle, progress_data=None, download_id=None):
    state_str = ['queued', 'checking', 'downloading metadata',
                 'downloading', 'finished', 'seeding', 'allocating']
    
    if download_id:
        with downloads_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["filename"] = handle.name() if handle.has_metadata() else "Obteniendo metadata..."
                active_downloads[download_id]["state"] = "downloading metadata"
    
    while handle.status().state != lt.torrent_status.seeding:
        s = handle.status()
        
        if progress_data is not None:
            progress_data["percent"] = round(s.progress * 100, 2)
            progress_data["speed"] = s.download_rate
            progress_data["state"] = state_str[s.state]
            progress_data["downloaded"] = s.total_done
            progress_data["total_size"] = s.total_wanted
        
        if download_id:
            with downloads_lock:
                if download_id in active_downloads:
                    active_downloads[download_id].update({
                        "percent": round(s.progress * 100, 2),
                        "speed": s.download_rate,
                        "state": state_str[s.state],
                        "downloaded": s.total_done,
                        "total_size": s.total_wanted,
                        "filename": handle.name() if handle.has_metadata() else "Obteniendo metadata...",
                        "last_update": datetime.datetime.now().isoformat()
                    })
        
        log(f"{s.progress * 100:.2f}% | ↓ {s.download_rate / 1000:.1f} kB/s | ↑ {s.upload_rate / 1000:.1f} kB/s | peers: {s.num_peers} | estado: {state_str[s.state]}")
        await asyncio.sleep(5)

def move_completed_files(temp_path, final_path):
    for root, _, files in os.walk(temp_path):
        for file in files:
            src = os.path.join(root, file)
            rel_path = os.path.relpath(src, temp_path)
            dst = os.path.join(final_path, rel_path)

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            log(f"📦 Archivo movido: {rel_path}")

def get_download_progress():
    with downloads_lock:
        return active_downloads.copy()

def cleanup_old_downloads(max_age_hours=24):
    with downloads_lock:
        now = datetime.datetime.now()
        to_remove = []
        for download_id, info in active_downloads.items():
            if "end_time" in info or "start_time" in info:
                end_time_str = info.get("end_time", info.get("start_time"))
                try:
                    end_time = datetime.datetime.fromisoformat(end_time_str)
                    if (now - end_time).total_seconds() > max_age_hours * 3600:
                        to_remove.append(download_id)
                except:
                    pass
        
        for download_id in to_remove:
            del active_downloads[download_id]

async def download_torrent_file(link):
    temp_path = os.path.join(TEMP_DIR, f"temp_{uuid.uuid4().hex}.torrent")
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    log("Descargando archivo .torrent...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                if response.status == 200:
                    async with aiofiles.open(temp_path, 'wb') as f:
                        await f.write(await response.read())
                    log("Archivo .torrent descargado exitosamente")
                    return temp_path
                else:
                    log(f"Error al descargar torrent: {response.status}")
                    return None
    except Exception as e:
        log(f"Error en descarga torrent: {e}")
        return None

def add_torrent_from_file(ses, torrent_path, save_path):
    try:
        info = lt.torrent_info(torrent_path)
        params = {
            'save_path': save_path,
            'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            'ti': info
        }
        handle = ses.add_torrent(params)
        handle.set_sequential_download(False)
        return handle
    except Exception as e:
        log(f"Error al agregar torrent desde archivo: {e}")
        raise

async def download_from_magnet_or_torrent(link, save_path=BASE_DIR, progress_data=None, download_id=None):
    try:
        unique_dir = str(uuid.uuid4())
        temp_download_path = os.path.join(TEMP_DIR, unique_dir)
        final_save_path = os.path.join(save_path, unique_dir)
        
        os.makedirs(temp_download_path, exist_ok=True)

        if download_id:
            with downloads_lock:
                active_downloads[download_id] = {
                    "link": link,
                    "percent": 0,
                    "state": "starting",
                    "filename": "Iniciando...",
                    "speed": 0,
                    "downloaded": 0,
                    "total_size": 0,
                    "start_time": datetime.datetime.now().isoformat(),
                    "last_update": datetime.datetime.now().isoformat(),
                    "unique_dir": unique_dir
                }

        ses = start_session()
        
        if link.endswith('.torrent'):
            torrent_path = await download_torrent_file(link)
            if not torrent_path:
                raise Exception("No se pudo descargar el archivo .torrent")
            
            handle = add_torrent_from_file(ses, torrent_path, temp_download_path)
        else:
            handle = add_torrent(ses, link, temp_download_path)

        begin = time.time()
        await wait_for_metadata(handle)

        if progress_data is not None:
            progress_data["filename"] = handle.name()

        await monitor_download(handle, progress_data, download_id)
        end = time.time()

        log(f"✅ {handle.name()} COMPLETADO")
        log(f"⏱️ Tiempo total: {int((end - begin) // 60)} min {int((end - begin) % 60)} seg")

        move_completed_files(temp_download_path, final_save_path)

        if link.endswith('.torrent'):
            try:
                os.remove(torrent_path)
            except:
                pass

        return final_save_path

    except Exception as e: 
        log(f"❌ Error en download_from_magnet_or_torrent: {e}")
        if download_id:
            with downloads_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["state"] = "error"
                    active_downloads[download_id]["error"] = str(e)
        raise e

async def handle_torrent_command(client, message, progress_data=None):
    try:
        full_text = message.text.strip()

        if not full_text:
            await message.reply("❗ Debes proporcionar un enlace después del comando.")
            return [], "", False

        use_compression = " -z" in full_text.lower()

        torrent_match = re.search(r'https?://[^\s]+\.torrent', full_text)
        magnet_match = re.search(r'magnet:\?[^\s]+', full_text)

        link = torrent_match.group(0) if torrent_match else (
            magnet_match.group(0) if magnet_match else ""
        )

        if not link:
            await message.reply("❗ El enlace debe ser un magnet o un archivo .torrent.")
            return [], "", False

        log(f"📥 Comando recibido con link: {link}")
        log(f"🗜️ Compresión: {use_compression}")

        download_id = str(uuid.uuid4())
        final_save_path = await download_from_magnet_or_torrent(
            link, BASE_DIR, progress_data, download_id
        )

        if not final_save_path or not os.path.exists(final_save_path):
            await message.reply("❌ No se descargaron archivos.")
            return [], "", False

        moved_files = []
        for root, _, files in os.walk(final_save_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, final_save_path)
                moved_files.append((rel_path, full_path))

        if not moved_files:
            await message.reply("❌ No se encontraron archivos descargados.")
            return [], "", False

        return moved_files, final_save_path, use_compression

    except Exception as e:
        log(f"❌ Error en handle_torrent_command: {e}")
        await message.reply(f"❌ Error al procesar el comando: {e}")
        return [], "", False

async def process_magnet_download_telegram(client, message, link, use_compression):
    async def safe_call(func, *args, **kwargs):
        while True:
            try:
                return await func(*args, **kwargs)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except MessageIdInvalid:
                return None
            except Exception as e:
                raise

    def format_time(seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    chat_id = message.chat.id
    status_msg = await safe_call(message.reply, "⏳ Iniciando descarga...")
    
    if not status_msg:
        return

    start_time = time.time()
    progress_data = {
        "filename": "", 
        "percent": 0, 
        "speed": 0.0, 
        "downloaded": 0, 
        "total_size": 0,
        "active": True
    }

    async def update_progress():
        while progress_data["percent"] < 100 and progress_data["active"]:
            try:
                elapsed = int(time.time() - start_time)
                formatted_time = format_time(elapsed)
                speed_mb = round(progress_data["speed"] / (1024 * 1024), 2)
                bar_length = 20
                filled_length = int(bar_length * progress_data["percent"] / 100)
                bar = "█" * filled_length + "▒" * (bar_length - filled_length)
                downloaded_mb = round(progress_data["downloaded"] / (1024 * 1024), 2)
                total_mb = round(progress_data["total_size"] / (1024 * 1024), 2) if progress_data["total_size"] > 0 else "Calculando..."
                await safe_call(status_msg.edit_text,
                    f"📥 **Descargando:** `{progress_data['filename']}`\n"
                    f"📊 **Progreso:** {progress_data['percent']}%\n"
                    f"📉 [{bar}]\n"
                    f"📦 **Tamaño:** {downloaded_mb} MB / {total_mb} MB\n"
                    f"🚀 **Velocidad:** {speed_mb} MB/s\n"
                    f"⏱️ **Tiempo:** {formatted_time}"
                )
            except Exception as e:
                break
            await asyncio.sleep(10)

    progress_task = asyncio.create_task(update_progress())

    try:
        if use_compression:
            message.text = f"/magnet -z {link}"
        else:
            message.text = f"/magnet {link}"

        result = await handle_torrent_command(client, message, progress_data)
        if not result or len(result) != 3:
            raise Exception("Error en la descarga")

        files, final_save_path, use_compression = result
        progress_data["percent"] = 100
        progress_data["active"] = False

        await asyncio.sleep(2)
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

        if not files:
            await safe_call(status_msg.edit_text, "❌ No se descargaron archivos.")
            await asyncio.sleep(5)
            await safe_call(status_msg.delete)
            return

        total_files = len(files)
        sent_count = 0
        total_size = sum(os.path.getsize(full_path) for _, full_path in files)
        total_mb = total_size / (1024 * 1024)
        sent_mb = 0
        current_file_name = ""
        current_mb_sent = 0

        def upload_progress(current, total):
            nonlocal current_mb_sent
            current_mb_sent = current / (1024 * 1024)

        await safe_call(status_msg.edit_text, "📤 Preparando envío de archivos...")

        async def update_upload_progress():
            while sent_count < total_files:
                try:
                    elapsed = int(time.time() - start_time)
                    formatted_time = format_time(elapsed)
                    estimated_ratio = (sent_mb + current_mb_sent) / total_mb if total_mb > 0 else 0
                    bar_length = 20
                    filled_length = int(bar_length * estimated_ratio)
                    bar = "█" * filled_length + "▒" * (bar_length - filled_length)
                    await safe_call(status_msg.edit_text,
                        f"📤 **Enviando archivos...**\n"
                        f"📁 **Archivos:** {sent_count}/{total_files}\n"
                        f"📊 **Progreso:** {sent_mb + current_mb_sent:.2f} MB / {total_mb:.2f} MB\n"
                        f"📉 [{bar}] {estimated_ratio*100:.1f}%\n"
                        f"⏱️ **Tiempo:** {formatted_time}\n"
                        f"📄 **Archivo actual:** {current_file_name}"
                    )
                except Exception as e:
                    break
                await asyncio.sleep(5)

        upload_task = asyncio.create_task(update_upload_progress())

        try:
            if use_compression:
                try:
                    await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                    await safe_call(status_msg.edit_text, "🗜️ Comprimiendo archivos...")
                    clean_name = clean_filename(progress_data.get('filename', 'archivos'))
                    archive_path = os.path.join(final_save_path, clean_name)
                    cmd_args = [
                        SEVEN_ZIP_EXE,
                        'a',
                        '-mx=0',
                        '-v2000m',
                        archive_path,
                        "."
                    ]
                    result = subprocess.run(cmd_args, cwd=final_save_path, capture_output=True, text=True, timeout=3600)
                    if result.returncode != 0:
                        raise Exception(f"Error en 7z: {result.stderr}")
                    archive_parts = sorted([
                        f for f in os.listdir(final_save_path)
                        if f.startswith(clean_name.replace('.7z', '')) and (f.endswith('.7z') or '.7z.' in f)
                    ])
                    if not archive_parts:
                        raise Exception("No se crearon archivos comprimidos")
                    total_parts = len(archive_parts)
                    for part in archive_parts:
                        full_path = os.path.join(final_save_path, part)
                        current_file_name = part
                        current_mb_sent = 0
                        part_size = os.path.getsize(full_path) / (1024 * 1024)
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, chat_id, document=full_path, progress=upload_progress, thumb=thumb)
                        sent_mb += part_size
                        sent_count += 1
                        try:
                            os.remove(full_path)
                        except:
                            pass
                    return
                except Exception as e:
                    await safe_call(message.reply, f"⚠️ Error al comprimir: {e}. Enviando archivos sin comprimir.")
                    use_compression = False

            for rel_path, full_path in files:
                try:
                    if not os.path.exists(full_path):
                        continue
                    current_file_name = os.path.basename(full_path)
                    file_size = os.path.getsize(full_path)
                    file_size_mb = file_size / (1024 * 1024)
                    current_mb_sent = 0
                    if file_size > 2000 * 1024 * 1024:
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(status_msg.edit_text, f"📦 Dividiendo archivo grande: {current_file_name}")
                        with open(full_path, 'rb') as original:
                            part_num = 1
                            while True:
                                part_data = original.read(2000 * 1024 * 1024)
                                if not part_data:
                                    break
                                part_file = f"{full_path}.part{part_num:03d}"
                                with open(part_file, 'wb') as part:
                                    part.write(part_data)
                                current_file_name = os.path.basename(part_file)
                                current_mb_sent = 0
                                part_size = os.path.getsize(part_file) / (1024 * 1024)
                                await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                                await safe_call(client.send_document, chat_id, document=part_file, progress=upload_progress, thumb=thumb)
                                sent_mb += part_size
                                try:
                                    os.remove(part_file)
                                except:
                                    pass
                                part_num += 1
                        try:
                            os.remove(full_path)
                        except:
                            pass
                        sent_count += 1
                    else:
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, chat_id, document=full_path, progress=upload_progress, thumb=thumb)
                        sent_mb += file_size_mb
                        sent_count += 1
                        try:
                            os.remove(full_path)
                        except:
                            pass
                except Exception as e:
                    await safe_call(message.reply, f"⚠️ Error al enviar {rel_path}: {e}")
        finally:
            upload_task.cancel()
            try:
                await upload_task
            except asyncio.CancelledError:
                pass

        await safe_call(status_msg.edit_text, "✅ Todos los archivos han sido enviados.")
        await asyncio.sleep(5)
        await safe_call(status_msg.delete)

    except Exception as e:
        progress_data["active"] = False
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass
        error_msg = await safe_call(message.reply, f"❌ Error durante la descarga: {e}")
        if status_msg:
            await safe_call(status_msg.delete)
