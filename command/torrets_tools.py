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
import time
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import tempfile

nyaa_cache = {}
CACHE_DURATION = 600
SEVEN_ZIP_EXE = os.path.join("7z", "7zz")
BASE_DIR = "vault_files/torrent_dl"
TEMP_DIR = os.path.join(BASE_DIR, "downloading")

active_downloads = {}
downloads_lock = threading.Lock()

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def search_nyaa(query):
    import requests
    from bs4 import BeautifulSoup
    import urllib.parse

    base_url = "https://nyaa.si/"
    search_query = urllib.parse.quote_plus(query)
    page = 1
    results = []
    previous_results = []
    
    while True:
        url = f"{base_url}?q={search_query}&f=0&c=0_0&p={page}"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_='torrent-list')
            
            if not table:
                break
                
            current_page_results = []
            rows = table.find_all('tr')[1:]
            
            for row in rows:
                try:
                    name_link = row.find('a', href=lambda x: x and '/view/' in x)
                    if not name_link:
                        continue
                    
                    name = name_link.get_text(strip=True)
                    
                    torrent_link = None
                    magnet_link = None
                    
                    download_links = row.find_all('a')
                    for link in download_links:
                        href = link.get('href', '')
                        if href.startswith('/download/'):
                            torrent_link = f"https://nyaa.si{href}"
                        elif href.startswith('magnet:'):
                            magnet_link = href
                    
                    size_td = row.find('td', class_='text-center', string=lambda x: x and 'MiB' in x)
                    size = size_td.get_text(strip=True) if size_td else "N/A"
                    
                    date_td = row.find('td', class_='text-center', attrs={'data-timestamp': True})
                    date = date_td.get_text(strip=True) if date_td else "N/A"
                    
                    current_page_results.append({
                        'name': name,
                        'torrent': torrent_link,
                        'magnet': magnet_link,
                        'size': size,
                        'date': date
                    })
                    
                except Exception as e:
                    continue
            
            if not current_page_results:
                break
                
            if previous_results and current_page_results == previous_results:
                break
                
            results.extend(current_page_results)
            previous_results = current_page_results
            page += 1
            
        except requests.RequestException:
            break
        except Exception as e:
            break
    
    output = ""
    for i, result in enumerate(results, 1):
        output += f"Resultado {i}\n"
        output += f"{result['name']}\n"
        output += f"Tamaño: {result['size']}\n"
        output += f"Fecha: {result['date']}\n"
        if result['torrent']:
            output += f"Link de Torrent: {result['torrent']}\n"
        if result['magnet']:
            output += f"Link de Magnet: {result['magnet']}\n"
        output += "\n"
    
    return output


async def search_in_nyaa(client, message, search_query):
    current_time = time.time()
    expired_keys = [key for key, data in nyaa_cache.items() if current_time - data['timestamp'] > CACHE_DURATION]
    for key in expired_keys:
        del nyaa_cache[key]
    cache_key = f"{message.chat.id}_{search_query.lower()}"
    
    if cache_key in nyaa_cache:
        results = nyaa_cache[cache_key]['results']
    else:
        results_data = search_nyaa(search_query)
        if not results_data.strip():
            await message.reply("❌ No se encontraron resultados para tu búsqueda.")
            return
        
        results = []
        current_result = {}
        for line in results_data.split('\n'):
            line = line.strip()
            if line.startswith('Resultado'):
                if current_result:
                    results.append(current_result)
                current_result = {'index': int(line.split()[1])}
            elif line and not line.startswith(('Link de Torrent:', 'Link de Magnet:')):
                if 'name' not in current_result:
                    current_result['name'] = line
                elif line.startswith('Tamaño:'):
                    current_result['size'] = line.replace('Tamaño: ', '')
                elif line.startswith('Fecha:'):
                    current_result['date'] = line.replace('Fecha: ', '')
            elif line.startswith('Link de Torrent:'):
                current_result['torrent'] = line.replace('Link de Torrent: ', '')
            elif line.startswith('Link de Magnet:'):
                current_result['magnet'] = line.replace('Link de Magnet: ', '')
        
        if current_result:
            results.append(current_result)
    
        nyaa_cache[cache_key] = {
            'results': results,
            'timestamp': current_time,
            'current_index': 0
        }
        
    await show_nyaa_result(client, message, cache_key, 0)

async def show_nyaa_result(client, message, cache_key, index):
    if cache_key not in nyaa_cache:
        await message.reply("❌ Los resultados de búsqueda han expirado.")
        return
    
    cache_data = nyaa_cache[cache_key]
    results = cache_data['results']
    
    if index < 0 or index >= len(results):
        await message.reply("❌ Índice de resultado inválido.")
        return
    
    result = results[index]
    cache_data['current_index'] = index
    
    keyboard = []
    row_buttons = []
    if 'torrent' in result:
        row_buttons.append(InlineKeyboardButton("📥 Torrent", callback_data=f"nyaa_torrent:{cache_key}:{index}"))
    if 'magnet' in result:
        row_buttons.append(InlineKeyboardButton("🧲 Magnet", callback_data=f"nyaa_magnet:{cache_key}:{index}"))
    
    if row_buttons:
        keyboard.append(row_buttons)
    
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"nyaa_prev:{cache_key}:{index}"))
        nav_buttons.append(InlineKeyboardButton("⏪", callback_data=f"nyaa_first:{cache_key}"))
    if index < len(results) - 1:
        nav_buttons.append(InlineKeyboardButton("⏩", callback_data=f"nyaa_next:{cache_key}:{index}"))
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"nyaa_last:{cache_key}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    message_text = f"**Resultado {index + 1}/{len(results)}**\n"
    message_text += f"**Nombre:** {result['name']}\n"
    message_text += f"**Fecha:** {result.get('date', 'N/A')}\n"
    message_text += f"**Tamaño:** {result.get('size', 'N/A')}"
    
    if cache_data.get('message_id'):
        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=cache_data['message_id'],
                text=message_text,
                reply_markup=reply_markup
            )
            return
        except:
            pass
    
    sent_message = await message.reply(message_text, reply_markup=reply_markup)
    cache_data['message_id'] = sent_message.id

async def handle_nyaa_callback(client, callback_query):
    data = callback_query.data
    parts = data.split(':')
    
    if len(parts) < 2:
        await callback_query.answer("❌ Error en los datos")
        return
    
    action = parts[0]
    cache_key = parts[1]
    
    if cache_key not in nyaa_cache:
        await callback_query.answer("❌ Los resultados han expirado")
        await callback_query.message.delete()
        return
    
    cache_data = nyaa_cache[cache_key]
    results = cache_data['results']
    
    if action == "nyaa_torrent":
        index = int(parts[2])
        result = results[index]
        await callback_query.answer("📥 Descargando torrent...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(result['torrent']) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.torrent') as temp_file:
                            temp_path = temp_file.name
                            temp_file.write(content)
                        
                        await client.send_document(
                            chat_id=callback_query.message.chat.id,
                            document=temp_path,
                            caption=f"📥 {result['name']}"
                        )
                        
                        os.unlink(temp_path)
                    else:
                        await callback_query.message.reply("❌ No se pudo descargar el archivo torrent")
                        
        except Exception as e:
            await callback_query.message.reply(f"❌ Error al descargar torrent: {e}")
        
    elif action == "nyaa_magnet":
        index = int(parts[2])
        result = results[index]
        await callback_query.answer("🧲 Enviando magnet...")
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text=result['magnet']
        )
        
    elif action == "nyaa_prev":
        index = int(parts[2])
        new_index = max(0, index - 1)
        await show_nyaa_result(client, callback_query.message, cache_key, new_index)
        await callback_query.answer()
        
    elif action == "nyaa_next":
        index = int(parts[2])
        new_index = min(len(results) - 1, index + 1)
        await show_nyaa_result(client, callback_query.message, cache_key, new_index)
        await callback_query.answer()
        
    elif action == "nyaa_first":
        await show_nyaa_result(client, callback_query.message, cache_key, 0)
        await callback_query.answer()
        
    elif action == "nyaa_last":
        await show_nyaa_result(client, callback_query.message, cache_key, len(results) - 1)
        await callback_query.answer()
        
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

async def download_from_magnet(link, save_path=BASE_DIR, progress_data=None, download_id=None):
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)

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

        if download_id:
            with downloads_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["state"] = "completed"
                    active_downloads[download_id]["percent"] = 100
                    active_downloads[download_id]["end_time"] = datetime.datetime.now().isoformat()

    except Exception as e:
        log(f"❌ Error en descarga: {e}")
        if download_id:
            with downloads_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["state"] = "error"
                    active_downloads[download_id]["error"] = str(e)

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
            del active_downloads[download
