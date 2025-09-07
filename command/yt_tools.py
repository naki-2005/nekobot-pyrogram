import os
import yt_dlp
import asyncio
import time
import uuid
import threading
import random
from pyrogram import enums
from pyrogram.errors import FloodWait, MessageIdInvalid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = "vault_files/yt_dl"
TEMP_DIR = os.path.join(BASE_DIR, "downloading")
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

active_downloads = {}
downloads_lock = threading.Lock()

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

async def safe_call(func, *args, **kwargs):
    while True:
        try:
            return await func(*args, **kwargs)
        except FloodWait as e:
            log(f"⏳ Esperando {e.value} seg para continuar")
            await asyncio.sleep(e.value)
        except MessageIdInvalid:
            log("⚠️ El mensaje ya no existe, no se puede editar")
            return None
        except Exception as e:
            log(f"❌ Error inesperado en {func.__name__}: {type(e).__name__}: {e}")
            raise

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_size(bytes_size):
    if bytes_size == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB']
    i = 0
    while bytes_size >= 1024 and i < len(units) - 1:
        bytes_size /= 1024.0
        i += 1
    
    return f"{bytes_size:.2f} {units[i]}"

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]
    return random.choice(user_agents)

def get_youtube_cookies():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)
        
        chrome_path = os.path.join(base_dir, "selenium", "chrome-linux64", "chrome")
        driver_path = os.path.join(base_dir, "selenium", "chromedriver-linux64", "chromedriver")
        
        if not os.path.exists(chrome_path):
            log(f"❌ Chrome no encontrado en: {chrome_path}")
            return False
        if not os.path.exists(driver_path):
            log(f"❌ ChromeDriver no encontrado en: {driver_path}")
            return False
        
        chrome_options = Options()
        chrome_options.binary_location = chrome_path
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={get_random_user_agent()}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = webdriver.chrome.service.Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            log("🌐 Navegando a YouTube...")
            driver.get("https://www.youtube.com")
            
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(5)
            
            cookies = driver.get_cookies()
            if not cookies:
                log("❌ No se pudieron obtener cookies")
                return False
            
            with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
                for cookie in cookies:
                    f.write(f"{cookie.get('domain', '.youtube.com')}\t"
                           f"{'TRUE' if cookie.get('secure', False) else 'FALSE'}\t"
                           f"{cookie.get('path', '/')}\t"
                           f"{'TRUE' if cookie.get('secure', False) else 'FALSE'}\t"
                           f"{int(time.time()) + 3600 * 24 * 7}\t"
                           f"{cookie.get('name', '')}\t"
                           f"{cookie.get('value', '')}\n")
            
            log(f"✅ {len(cookies)} cookies obtenidas exitosamente")
            return True
            
        except Exception as e:
            log(f"❌ Error al obtener cookies: {e}")
            return False
        finally:
            try:
                driver.quit()
            except:
                pass
            
    except Exception as e:
        log(f"❌ Error al iniciar el navegador: {e}")
        return False

def download_youtube_video_sync(url, download_id, progress_data=None, audio_only=False):
    try:
        with downloads_lock:
            active_downloads[download_id] = {
                "url": url,
                "percent": 0,
                "state": "starting",
                "filename": "Obteniendo información...",
                "speed": 0,
                "downloaded": 0,
                "total_size": 0,
                "start_time": time.time(),
                "last_update": time.time(),
                "audio_only": audio_only
            }
        
        ydl_opts = {
            'outtmpl': os.path.join(TEMP_DIR, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'continuedl': True,
            'concurrent_fragment_downloads': 3,
            'retries': 10,
            'noprogress': False,
            'extractor_retries': 5,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'ignoreerrors': False,
            'socket_timeout': 30,
            'extract_flat': False,
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        }
        
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE
            log("✅ Usando cookies para autenticación")
        else:
            log("⚠️ Continuando sin cookies, intentando obtener...")
            if get_youtube_cookies() and os.path.exists(COOKIES_FILE):
                ydl_opts['cookiefile'] = COOKIES_FILE
                log("✅ Cookies obtenidas automáticamente")
        
        ydl_opts['http_headers']['User-Agent'] = get_random_user_agent()
        
        if audio_only:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '192K',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            })
        else:
            ydl_opts['format'] = 'best[height<=720]'
        
        def progress_hook(d):
            if d.get('status') == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                filename = d.get('filename', '')
                
                if total and total > 0:
                    percent = (downloaded / total) * 100
                    
                    if progress_data is not None:
                        progress_data["percent"] = percent
                        progress_data["speed"] = speed
                        progress_data["downloaded"] = downloaded
                        progress_data["total_size"] = total
                        progress_data["filename"] = os.path.basename(filename) if filename else "Descargando..."
                    
                    with downloads_lock:
                        if download_id in active_downloads:
                            active_downloads[download_id].update({
                                "percent": percent,
                                "speed": speed,
                                "downloaded": downloaded,
                                "total_size": total,
                                "filename": os.path.basename(filename) if filename else "Descargando...",
                                "state": "downloading",
                                "last_update": time.time()
                            })
            
            elif d.get('status') == 'finished':
                with downloads_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id].update({
                            "percent": 100,
                            "state": "completed",
                            "last_update": time.time(),
                            "end_time": time.time()
                        })
                
                if progress_data is not None:
                    progress_data["percent"] = 100
                    progress_data["state"] = "completed"
        
        ydl_opts['progress_hooks'] = [progress_hook]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("No se pudo obtener información del video")
            
            filename = download_youtube_video_sync(url, download_id, progress_data, audio_only)
            
            if audio_only:
                base_name = os.path.splitext(filename)[0]
                mp3_file = base_name + '.mp3'
                if os.path.exists(mp3_file):
                    return mp3_file
            return filename
            
    except Exception as e:
        log(f"❌ Error en descarga de YouTube: {e}")
        with downloads_lock:
            if download_id in active_downloads:
                active_downloads[download_id].update({
                    "state": "error",
                    "error": str(e),
                    "last_update": time.time()
                })
        
        if progress_data is not None:
            progress_data["state"] = "error"
            progress_data["error"] = str(e)
        
        raise

async def handle_yt_dl(client, message, text):
    try:
        parts = text.strip().split()
        
        if len(parts) < 2:
            await message.reply("❗ Debes proporcionar una URL de YouTube después del comando.")
            return
        
        url = parts[1].strip()
        
        if "youtube.com" not in url and "youtu.be" not in url:
            await message.reply("❗ URL no válida. Debe ser un enlace de YouTube.")
            return
        
        audio_only = False
        if len(parts) > 2 and parts[2].strip() == "-a":
            audio_only = True
        
        chat_id = message.chat.id
        
        cookies_status = ""
        if not os.path.exists(COOKIES_FILE):
            cookies_status = "\n⚠️ **Generando cookies automáticamente...**"
        
        status_msg = await message.reply(f"⏳ Iniciando descarga de YouTube...{cookies_status}")
        
        start_time = time.time()
        progress_data = {
            "filename": "", 
            "percent": 0, 
            "speed": 0, 
            "downloaded": 0, 
            "total_size": 0,
            "state": "starting",
            "active": True
        }
        
        download_id = str(uuid.uuid4())
        
        async def update_progress():
            while progress_data["percent"] < 100 and progress_data["active"]:
                try:
                    elapsed = int(time.time() - start_time)
                    formatted_time = format_time(elapsed)
                    speed_mb = progress_data["speed"] / (1024 * 1024) if progress_data["speed"] > 0 else 0
                    
                    bar_length = 20
                    filled_length = int(bar_length * progress_data["percent"] / 100)
                    bar = "█" * filled_length + "▒" * (bar_length - filled_length)
                    
                    status_text = (
                        f"📥 **Descargando de YouTube:**\n"
                        f"📄 **Archivo:** `{progress_data.get('filename', '')}`\n"
                        f"📊 **Progreso:** {progress_data.get('percent', 0):.1f}%\n"
                        f"📉 [{bar}]\n"
                        f"📦 **Descargado:** {format_size(progress_data.get('downloaded', 0))} / {format_size(progress_data.get('total_size', 0))}\n"
                        f"🚀 **Velocidad:** {speed_mb:.2f} MB/s\n"
                        f"⏱️ **Tiempo:** {formatted_time}\n"
                        f"🔊 **Modo:** {'Solo audio' if audio_only else 'Video completo'}"
                    )
                    
                    await safe_call(status_msg.edit_text, status_text)
                except Exception as e:
                    log(f"Error en update_progress: {e}")
                    break
                await asyncio.sleep(3)
        
        progress_task = asyncio.create_task(update_progress())
        
        try:
            downloaded_file = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: download_youtube_video_sync(url, download_id, progress_data, audio_only)
            )
            
            progress_data["active"] = False
            await asyncio.sleep(2)
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                await safe_call(status_msg.edit_text, "❌ Error: No se pudo descargar el archivo.")
                return
            
            file_size = os.path.getsize(downloaded_file)
            file_size_mb = file_size / (1024 * 1024)
            filename = os.path.basename(downloaded_file)
            
            await safe_call(status_msg.edit_text, f"📤 Preparando envío: {filename} ({file_size_mb:.2f} MB)")
            
            await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
            
            if audio_only:
                await safe_call(client.send_audio, 
                               chat_id=chat_id, 
                               audio=downloaded_file,
                               caption=f"🎵 {filename}")
            else:
                await safe_call(client.send_video, 
                               chat_id=chat_id, 
                               video=downloaded_file,
                               caption=f"🎥 {filename}")
            
            try:
                os.remove(downloaded_file)
            except:
                pass
            
            await safe_call(status_msg.edit_text, "✅ Descarga y envío completados correctamente.")
            await asyncio.sleep(3)
            await safe_call(status_msg.delete)
            
        except Exception as e:
            progress_data["active"] = False
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            error_msg = f"❌ Error durante la descarga: {str(e)}"
            await safe_call(status_msg.edit_text, error_msg)
            await asyncio.sleep(10)
            await safe_call(status_msg.delete)
            
    except Exception as e:
        log(f"Error en handle_yt_dl: {e}")
        await message.reply(f"❌ Error al procesar el comando: {str(e)}")

async def handle_get_cookies(client, message):
    try:
        status_msg = await message.reply("🔄 Generando cookies de YouTube...")
        
        success = await asyncio.get_event_loop().run_in_executor(None, get_youtube_cookies)
        
        if success:
            await safe_call(status_msg.edit_text, "✅ Cookies generadas exitosamente. Ahora puedes descargar videos sin problemas.")
        else:
            await safe_call(status_msg.edit_text, "❌ Error al generar cookies. Verifica que Selenium esté configurado correctamente.")
            
    except Exception as e:
        log(f"Error en handle_get_cookies: {e}")
        await message.reply(f"❌ Error al generar cookies: {str(e)}")
