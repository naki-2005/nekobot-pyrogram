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
import requests
from bs4 import BeautifulSoup
import urllib.parse
from pyrogram import enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

nyaa_cache = {}
sukebei_cache = {}
CACHE_DURATION = 600
SEVEN_ZIP_EXE = os.path.join("7z", "7zz")
BASE_DIR = "vault_files/torrent_dl"
TEMP_DIR = os.path.join(BASE_DIR, "downloading")

active_downloads = {}
downloads_lock = threading.Lock()

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def clean_filename(name):
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáéíóúÁÉÍÓÚ0123456789 ()[]"
    cleaned = ''.join(c for c in name if c in allowed_chars)
    return cleaned[:50] + '.7z' if len(cleaned) > 50 else cleaned + '.7z'

def search_nyaa(query):
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
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"nyaa_prev:{cache_key}"))
        nav_buttons.append(InlineKeyboardButton("⏪", callback_data=f"nyaa_first:{cache_key}"))
    if index < len(results) - 1:
        nav_buttons.append(InlineKeyboardButton("⏩", callback_data=f"nyaa_last:{cache_key}"))
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"nyaa_next:{cache_key}"))
    
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
    current_index = cache_data['current_index']
    
    if action == "nyaa_torrent":
        index = int(parts[2])
        result = results[index]
        
        await callback_query.answer("📥 Enviando link de torrent...")
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text=result['torrent']
        )
        
    elif action == "nyaa_magnet":
        index = int(parts[2])
        result = results[index]
        await callback_query.answer("🧲 Enviando magnet...")
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text=result['magnet']
        )
        
    elif action == "nyaa_prev":
        new_index = max(0, current_index - 1)
        await show_nyaa_result(client, callback_query.message, cache_key, new_index)
        await callback_query.answer()
        
    elif action == "nyaa_next":
        new_index = min(len(results) - 1, current_index + 1)
        await show_nyaa_result(client, callback_query.message, cache_key, new_index)
        await callback_query.answer()
        
    elif action == "nyaa_first":
        await show_nyaa_result(client, callback_query.message, cache_key, 0)
        await callback_query.answer()
        
    elif action == "nyaa_last":
        await show_nyaa_result(client, callback_query.message, cache_key, len(results) - 1)
        await callback_query.answer()
        
def search_sukebei(query):
    base_url = "https://sukebei.nyaa.si/"
    search_query = urllib.parse.quote_plus(query)
    page = 1
    results = []
    
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
            
            if not rows:
                break
                
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
                            torrent_link = f"https://sukebei.nyaa.si{href}"
                        elif href.startswith('magnet:'):
                            magnet_link = href
                    
                    size_td = row.find('td', class_='text-center', string=lambda x: x and 'MiB' in x or 'GiB' in x)
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
                
            results.extend(current_page_results)
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

async def search_in_sukebei(client, message, search_query):
    current_time = time.time()
    expired_keys = [key for key, data in sukebei_cache.items() if current_time - data['timestamp'] > CACHE_DURATION]
    for key in expired_keys:
        del sukebei_cache[key]
    cache_key = f"sukebei_{message.chat.id}_{search_query.lower()}"
    
    if cache_key in sukebei_cache:
        results = sukebei_cache[cache_key]['results']
    else:
        results_data = search_sukebei(search_query)
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
    
        sukebei_cache[cache_key] = {
            'results': results,
            'timestamp': current_time,
            'current_index': 0
        }
        
    await show_sukebei_result(client, message, cache_key, 0)

async def show_sukebei_result(client, message, cache_key, index):
    if cache_key not in sukebei_cache:
        await message.reply("❌ Los resultados de búsqueda han expirado.")
        return
    
    cache_data = sukebei_cache[cache_key]
    results = cache_data['results']
    
    if index < 0 or index >= len(results):
        await message.reply("❌ Índice de resultado inválido.")
        return
    
    result = results[index]
    cache_data['current_index'] = index
    
    keyboard = []
    row_buttons = []
    if 'torrent' in result:
        row_buttons.append(InlineKeyboardButton("📥 Torrent", callback_data=f"sukebei_torrent:{cache_key}:{index}"))
    if 'magnet' in result:
        row_buttons.append(InlineKeyboardButton("🧲 Magnet", callback_data=f"sukebei_magnet:{cache_key}:{index}"))
    
    if row_buttons:
        keyboard.append(row_buttons)
    
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"sukebei_prev:{cache_key}"))
        nav_buttons.append(InlineKeyboardButton("⏪", callback_data=f"sukebei_first:{cache_key}"))
    if index < len(results) - 1:
        nav_buttons.append(InlineKeyboardButton("⏩", callback_data=f"sukebei_last:{cache_key}"))
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"sukebei_next:{cache_key}"))
    
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

async def handle_sukebei_callback(client, callback_query):
    data = callback_query.data
    parts = data.split(':')
    
    if len(parts) < 2:
        await callback_query.answer("❌ Error en los datos")
        return
    
    action = parts[0]
    cache_key = parts[1]
    
    if cache_key not in sukebei_cache:
        await callback_query.answer("❌ Los resultados han expirado")
        await callback_query.message.delete()
        return
    
    cache_data = sukebei_cache[cache_key]
    results = cache_data['results']
    current_index = cache_data['current_index']
    
    if action == "sukebei_torrent":
        index = int(parts[2])
        result = results[index]
        
        await callback_query.answer("📥 Enviando link de torrent...")
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text=result['torrent']
        )
        
    elif action == "sukebei_magnet":
        index = int(parts[2])
        result = results[index]
        await callback_query.answer("🧲 Enviando magnet...")
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text=result['magnet']
        )
        
    elif action == "sukebei_prev":
        new_index = max(0, current_index - 1)
        await show_sukebei_result(client, callback_query.message, cache_key, new_index)
        await callback_query.answer()
        
    elif action == "sukebei_next":
        new_index = min(len(results) - 1, current_index + 1)
        await show_sukebei_result(client, callback_query.message, cache_key, new_index)
        await callback_query.answer()
        
    elif action == "sukebei_first":
        await show_sukebei_result(client, callback_query.message, cache_key, 0)
        await callback_query.answer()
        
    elif action == "sukebei_last":
        await show_sukebei_result(client, callback_query.message, cache_key, len(results) - 1)
        await callback_query.answer()

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
        parts = message.text.strip().split()
        
        if len(parts) < 2:
            await message.reply("❗ Debes proporcionar un enlace después del comando.")
            return [], "", False

        use_compression = False
        if parts[1] == "-z":
            use_compression = True
            if len(parts) < 3:
                await message.reply("❗ Debes proporcionar un enlace después de -z.")
                return [], "", False
            link = parts[2]
        else:
            link = parts[1]

        if not (link.startswith("magnet:") or link.endswith(".torrent")):
            await message.reply("❗ El enlace debe ser un magnet o un archivo .torrent.")
            return [], "", False

        log(f"📥 Comando recibido con link: {link}")
        download_id = str(uuid.uuid4())
        final_save_path = await download_from_magnet_or_torrent(link, BASE_DIR, progress_data, download_id)

        moved_files = []
        for root, _, files in os.walk(final_save_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, final_save_path)
                moved_files.append((rel_path, full_path))

        return moved_files, final_save_path, use_compression

    except Exception as e:
        log(f"❌ Error en handle_torrent_command: {e}")
        await message.reply(f"❌ Error al procesar el comando: {e}")
        return [], "", False

async def process_magnet_download_telegram(client, message, link, use_compression):
    from pyrogram.errors import FloodWait, MessageIdInvalid

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
                print(f"Error en update_progress: {e}")
                break
                
            await asyncio.sleep(10)

    progress_task = asyncio.create_task(update_progress())
    
    try:
        if use_compression:
            message.text = f"/magnet -z {link}"
        else:
            message.text = f"/magnet {link}"
            
        files, final_save_path, use_compression = await handle_torrent_command(client, message, progress_data)
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
        total_mb = sum(os.path.getsize(full_path) for _, full_path in files) / (1024 * 1024)
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

                    clean_name = clean_filename(progress_data['filename'])
                    archive_path = os.path.join(final_save_path, clean_name)
                    cmd_args = [
                        SEVEN_ZIP_EXE,
                        'a',
                        '-mx=0',
                        '-v2000m',
                        archive_path,
                        os.path.join(final_save_path, '*')
                    ]
                    subprocess.run(cmd_args, check=True, cwd=final_save_path)

                    for rel_path, full_path in files:
                        if os.path.exists(full_path):
                            os.remove(full_path)

                    archive_parts = sorted([
                        f for f in os.listdir(final_save_path)
                        if f.startswith(clean_name.replace('.7z', ''))
                    ])

                    total_parts = len(archive_parts)
                    for part in archive_parts:
                        full_path = os.path.join(final_save_path, part)
                        current_file_name = part
                        current_mb_sent = 0
                        part_size = os.path.getsize(full_path) / (1024 * 1024)
                        
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, chat_id, document=full_path, progress=upload_progress)
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                        
                        sent_mb += part_size
                        sent_count += 1
                        os.remove(full_path)

                    await safe_call(status_msg.edit_text,
                        f"📤 **Enviando archivos...**\n"
                        f"📁 **Partes:** {sent_count}/{total_parts}\n"
                        f"📊 **Progreso:** {sent_mb:.2f} MB / {total_mb:.2f} MB\n"
                        f"⏱️ **Tiempo:** {format_time(int(time.time() - start_time))}"
                    )

                except Exception as e:
                    await safe_call(message.reply, f"⚠️ Error al comprimir y enviar archivos: {e}")
                return

            for rel_path, full_path in files:
                try:
                    current_file_name = os.path.basename(full_path)
                    file_size = os.path.getsize(full_path)
                    file_size_mb = file_size / (1024 * 1024)
                    current_mb_sent = 0

                    if file_size > 2000 * 1024 * 1024:
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(status_msg.edit_text, f"📦 El archivo `{current_file_name}` excede los 2000MB. Dividiéndolo en partes...")

                        with open(full_path, 'rb') as original:
                            part_num = 1
                            while True:
                                part_data = original.read(2000 * 1024 * 1024)
                                if not part_data:
                                    break
                                part_file = f"{full_path}.{part_num:03d}"
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

                        os.remove(full_path)
                        sent_count += 1

                    else:
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
                        await safe_call(client.send_document, chat_id, document=full_path, progress=upload_progress)
                        await safe_call(client.send_chat_action, chat_id, enums.ChatAction.CANCEL)
                        
                        sent_mb += file_size_mb
                        sent_count += 1
                        os.remove(full_path)

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
