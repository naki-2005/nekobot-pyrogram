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
import uuid
from pyrogram import enums

SEVEN_ZIP_EXE = os.path.join("7z", "7zz")
BASE_DIR = "vault_files/torrent_dl"
TEMP_DIR = os.path.join(BASE_DIR, "downloading")

# Variable global para almacenar el progreso de las descargas
active_downloads = {}
downloads_lock = threading.Lock()

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_magnet_from_torrent(torrent_path):
    from torf import Torrent
    t = Torrent.read(torrent_path)
    return str(t.magnet(name=True, size=False, trackers=False, tracker=False))

async def download_torrent(link):
    if link.endswith('.torrent'):
        temp_path = os.path.join(TEMP_DIR, "temp.torrent")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        log("Descargando archivo .torrent...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(link) as response:
                    if response.status == 200:
                        async with aiofiles.open(temp_path, 'wb') as f:
                            await f.write(await response.read())
                        log("Archivo .torrent descargado")
                        link = get_magnet_from_torrent(temp_path)
                        log("Convertido a magnet link")
                    else:
                        log(f"Error al descargar torrent: {response.status}")
        except Exception as e:
            log(f"Error en descarga torrent: {e}")
    
    return link

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
    
    # Actualizar información inicial en active_downloads
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
        
        # Actualizar active_downloads
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

async def download_from_magnet(link, save_path=BASE_DIR, progress_data=None, download_id=None):
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)

        # Registrar la descarga en active_downloads
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
                    "last_update": datetime.datetime.now().isoformat()
                }

        link = await download_torrent(link)
        log(f"Usando magnet link: {link}")

        ses = start_session()
        handle = add_torrent(ses, link, TEMP_DIR)

        begin = time.time()
        await wait_for_metadata(handle)
        log(f"Iniciando descarga: {handle.name()}")

        if progress_data is not None:
            progress_data["filename"] = handle.name()

        await monitor_download(handle, progress_data, download_id)
        end = time.time()

        log(f"✅ {handle.name()} COMPLETADO")
        log(f"⏱️ Tiempo total: {int((end - begin) // 60)} min {int((end - begin) % 60)} seg")

        move_completed_files(TEMP_DIR, save_path)

        # Marcar como completado en active_downloads
        if download_id:
            with downloads_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["state"] = "completed"
                    active_downloads[download_id]["percent"] = 100
                    active_downloads[download_id]["end_time"] = datetime.datetime.now().isoformat()

    except Exception as e:
        log(f"❌ Error en descarga: {e}")
        # Marcar como error en active_downloads
        if download_id:
            with downloads_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["state"] = "error"
                    active_downloads[download_id]["error"] = str(e)

# Función para obtener el progreso de las descargas
def get_download_progress():
    with downloads_lock:
        return active_downloads.copy()

# Función para limpiar descargas antiguas
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

async def handle_torrent_command(client, message, progress_data=None):
    try:
        parts = message.text.strip().split(maxsplit=2)

        if len(parts) < 2:
            await message.reply("❗ Debes proporcionar un enlace después del comando.")
            return []

        arg1 = parts[1]
        link = parts[2] if arg1 == "-z" and len(parts) > 2 else arg1

        if not (link.startswith("magnet:") or link.endswith(".torrent")):
            await message.reply("❗ El enlace debe ser un magnet o un archivo .torrent.")
            return []

        log(f"📥 Comando recibido con link: {link}")
        download_id = str(uuid.uuid4())
        await download_from_magnet(link, BASE_DIR, progress_data, download_id)

        moved_files = []
        for root, _, files in os.walk(BASE_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, BASE_DIR)
                moved_files.append(rel_path)

        return moved_files

    except Exception as e:
        log(f"❌ Error en handle_torrent_command: {e}")
        await message.reply(f"❌ Error al procesar el comando: {e}")
        return []

async def process_magnet_download_telegram(client, message, arg_text, use_compression):
    import os
    import asyncio
    import subprocess
    import time
    from pyrogram import enums
    from pyrogram.errors import FloodWait, MessageIdInvalid

    async def safe_call(func, *args, **kwargs):
        while True:
            try:
                return await func(*args, **kwargs)
            except FloodWait as e:
                print(f"⏳ Esperando {e.value} seg para continuar")
                await asyncio.sleep(e.value)
            except MessageIdInvalid:
                print("⚠️ El mensaje ya no existe, no se puede editar")
                return None
            except Exception as e:
                print(f"❌ Error inesperado en {func.__name__}: {type(e).__name__}: {e}")
                raise

    def format_time(seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    chat_id = message.chat.id
    message.text = f"/magnet {arg_text}"
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
                print(f"Error en update_progress: {e}")
                break
                
            await asyncio.sleep(10)

    progress_task = asyncio.create_task(update_progress())
    
    try:
        download_id = str(uuid.uuid4())
        files = await handle_torrent_command(client, message, progress_data)
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
        total_mb = sum(os.path.getsize(os.path.join(BASE_DIR, rel_path)) for rel_path in files) / (1024 * 1024)
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
                    print(f"Error en update_upload_progress: {e}")
                    break
                await asyncio.sleep(10)

        upload_task = asyncio.create_task(update_upload_progress())

        try:
            if use_compression:
                try:
                    await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                    await safe_call(status_msg.edit_text, "🗜️ Comprimiendo archivos en partes de 2000MB con 7z...")

                    archive_path = os.path.join(BASE_DIR, "compressed.7z")
                    cmd_args = [
                        SEVEN_ZIP_EXE,
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

                    archive_parts = sorted([
                        f for f in os.listdir(BASE_DIR)
                        if f.startswith("compressed.7z")
                    ])

                    for part in archive_parts:
                        full_path = os.path.join(BASE_DIR, part)
                        current_file_name = part
                        current_mb_sent = 0
                        part_size = os.path.getsize(full_path) / (1024 * 1024)
                        
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, chat_id, document=full_path, progress=upload_progress)
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                        
                        sent_mb += part_size
                        sent_count += 1
                        os.remove(full_path)

                except Exception as e:
                    await safe_call(message.reply, f"⚠️ Error al comprimir y enviar archivos: {e}")
                return

            for rel_path in files:
                path = os.path.join(BASE_DIR, rel_path)
                try:
                    current_file_name = os.path.basename(path)
                    file_size = os.path.getsize(path)
                    file_size_mb = file_size / (1024 * 1024)
                    current_mb_sent = 0

                    if file_size > 2000 * 1024 * 1024:
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(status_msg.edit_text, f"📦 El archivo `{current_file_name}` excede los 2000MB. Dividiéndolo en partes...")

                        with open(path, 'rb') as original:
                            part_num = 1
                            while True:
                                part_data = original.read(2000 * 1024 * 1024)
                                if not part_data:
                                    break
                                part_file = f"{path}.{part_num:03d}"
                                with open(part_file, 'wb') as part:
                                    part.write(part_data)
                                
                                current_file_name = os.path.basename(part_file)
                                current_mb_sent = 0
                                part_size = os.path.getsize(part_file) / (1024 * 1024)
                                
                                await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                                await safe_call(client.send_document, chat_id, document=part_file, progress=upload_progress)
                                await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                                
                                sent_mb += part_size
                                os.remove(part_file)
                                part_num += 1

                        os.remove(path)
                        sent_count += 1

                    else:
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, chat_id, document=path, progress=upload_progress)
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                        
                        sent_mb += file_size_mb
                        sent_count += 1
                        os.remove(path)

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
