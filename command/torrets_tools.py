import os
import time
import datetime
import shutil
import libtorrent as lt
import asyncio
import subprocess
from pyrogram import enums
SEVEN_ZIP_EXE = os.path.join("7z", "7zz")
BASE_DIR = "vault_files/torrent_dl"
TEMP_DIR = os.path.join(BASE_DIR, "downloading")

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_magnet_from_torrent(torrent_path):
    from torf import Torrent
    t = Torrent.read(torrent_path)
    return str(t.magnet(name=True, size=False, trackers=False, tracker=False))

def download_torrent(link):
    if link.endswith('.torrent'):
        import wget
        temp_path = os.path.join(TEMP_DIR, "temp.torrent")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        log("Descargando archivo .torrent...")
        wget.download(link, temp_path)
        link = get_magnet_from_torrent(temp_path)
        log("Convertido a magnet link")
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

def wait_for_metadata(handle):
    log("Descargando metadata...")
    while not handle.has_metadata():
        time.sleep(1)
    log("Metadata obtenida")


async def monitor_download(handle, progress_data=None):
    state_str = ['queued', 'checking', 'downloading metadata',
                 'downloading', 'finished', 'seeding', 'allocating']
    while handle.status().state != lt.torrent_status.seeding:
        s = handle.status()
        log(f"{s.progress * 100:.2f}% | ↓ {s.download_rate / 1000:.1f} kB/s | ↑ {s.upload_rate / 1000:.1f} kB/s | peers: {s.num_peers} | estado: {state_str[s.state]}")
        if progress_data is not None:
            progress_data["percent"] = round(s.progress * 100, 2)
            progress_data["speed"] = s.download_rate / 1000
            progress_data["state"] = state_str[s.state]
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

async def download_from_magnet(link, save_path=BASE_DIR, progress_data=None):
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)

        link = download_torrent(link)
        log(f"Usando magnet link: {link}")

        ses = start_session()
        handle = add_torrent(ses, link, TEMP_DIR)

        begin = time.time()
        wait_for_metadata(handle)
        log(f"Iniciando descarga: {handle.name()}")

        if progress_data is not None:
            progress_data["filename"] = handle.name()

        await monitor_download(handle, progress_data)
        end = time.time()

        log(f"✅ {handle.name()} COMPLETADO")
        log(f"⏱️ Tiempo total: {int((end - begin) // 60)} min {int((end - begin) % 60)} seg")

        move_completed_files(TEMP_DIR, save_path)

    except Exception as e:
        log(f"❌ Error en descarga: {e}")

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
        await download_from_magnet(link, BASE_DIR, progress_data)

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
    (client, message, arg_text, use_compression):
    chat_id = message.chat.id
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

