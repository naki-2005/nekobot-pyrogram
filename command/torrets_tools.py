import os
import time
import datetime
import shutil
import libtorrent as lt

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

def monitor_download(handle):
    state_str = ['queued', 'checking', 'downloading metadata',
                 'downloading', 'finished', 'seeding', 'allocating']
    while handle.status().state != lt.torrent_status.seeding:
        s = handle.status()
        log(f"{s.progress * 100:.2f}% | ↓ {s.download_rate / 1000:.1f} kB/s | ↑ {s.upload_rate / 1000:.1f} kB/s | peers: {s.num_peers} | estado: {state_str[s.state]}")
        time.sleep(5)

def move_completed_files(temp_path, final_path):
    for root, _, files in os.walk(temp_path):
        for file in files:
            src = os.path.join(root, file)
            rel_path = os.path.relpath(src, temp_path)
            dst = os.path.join(final_path, rel_path)

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            log(f"📦 Archivo movido: {rel_path}")

def download_from_magnet(link, save_path=BASE_DIR):
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)

        link = download_torrent(link)
        log(f"Usando magnet link: {link}")

        ses = start_session()
        handle = add_torrent(ses, link, TEMP_DIR)

        begin = time.time()
        wait_for_metadata(handle)
        log(f"Iniciando descarga: {handle.name()}")
        monitor_download(handle)
        end = time.time()

        log(f"✅ {handle.name()} COMPLETADO")
        log(f"⏱️ Tiempo total: {int((end - begin) // 60)} min {int((end - begin) % 60)} seg")

        move_completed_files(TEMP_DIR, save_path)

    except Exception as e:
        log(f"❌ Error en descarga: {e}")


async def handle_torrent_command(client, message):
    try:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            message.reply("❗ Debes proporcionar un enlace después del comando.")
            return []

        link = parts[1]
        log(f"📥 Comando recibido con link: {link}")
        download_from_magnet(link)

        moved_files = []
        for root, _, files in os.walk(BASE_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, BASE_DIR)
                moved_files.append(rel_path)

        return moved_files

    except Exception as e:
        log(f"❌ Error en handle_torrent_command: {e}")
        message.reply(f"❌ Error al procesar el comando: {e}")
        return []
        
