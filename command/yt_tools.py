import os
import yt_dlp
import asyncio
import time
import uuid
import threading
from pyrogram import enums
from pyrogram.errors import FloodWait, MessageIdInvalid

# Configuración
BASE_DIR = "vault_files/yt_dl"
TEMP_DIR = os.path.join(BASE_DIR, "downloading")
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Variable global para almacenar el progreso de las descargas
active_downloads = {}
downloads_lock = threading.Lock()

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

async def safe_call(func, *args, **kwargs):
    """Maneja llamadas seguras a la API de Telegram"""
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
    """Formatea segundos a formato HH:MM:SS"""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_size(bytes_size):
    """Formatea bytes a formato legible"""
    if bytes_size == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB']
    i = 0
    while bytes_size >= 1024 and i < len(units) - 1:
        bytes_size /= 1024.0
        i += 1
    
    return f"{bytes_size:.2f} {units[i]}"

def get_download_progress():
    """Obtiene el progreso de todas las descargas activas"""
    with downloads_lock:
        return active_downloads.copy()

def cleanup_old_downloads(max_age_hours=24):
    """Limpia descargas antiguas del registro"""
    with downloads_lock:
        now = time.time()
        to_remove = []
        for download_id, info in active_downloads.items():
            if "start_time" in info:
                if (now - info["start_time"]) > max_age_hours * 3600:
                    to_remove.append(download_id)
        
        for download_id in to_remove:
            del active_downloads[download_id]

async def download_youtube_video(url, download_id, progress_data=None, audio_only=False):
    """
    Descarga un video de YouTube usando yt-dlp
    
    Args:
        url: URL del video de YouTube
        download_id: ID único para esta descarga
        progress_data: Diccionario para almacenar progreso
        audio_only: Si es True, descarga solo audio
    """
    try:
        # Registrar la descarga en active_downloads
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
        
        # Configuración de yt-dlp
        ydl_opts = {
            'outtmpl': os.path.join(TEMP_DIR, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'continuedl': True,
            'concurrent_fragment_downloads': 3,
            'retries': 10,
            'noprogress': False
        }
        
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
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
        
        # Hook de progreso personalizado
        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                filename = d.get('filename', '')
                
                if total > 0:
                    percent = (downloaded / total) * 100
                    
                    # Actualizar progress_data si se proporciona
                    if progress_data is not None:
                        progress_data["percent"] = percent
                        progress_data["speed"] = speed
                        progress_data["downloaded"] = downloaded
                        progress_data["total_size"] = total
                        progress_data["filename"] = os.path.basename(filename) if filename else "Descargando..."
                    
                    # Actualizar active_downloads
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
            
            elif d['status'] == 'finished':
                # Actualizar como completado
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
        
        # Realizar la descarga
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Para descargas de audio, el archivo final tiene extensión mp3
            if audio_only and filename.endswith('.webm'):
                filename = filename[:-5] + '.mp3'
            elif audio_only and filename.endswith('.m4a'):
                filename = filename[:-4] + '.mp3'
            
            return filename
            
    except Exception as e:
        log(f"❌ Error en descarga de YouTube: {e}")
        # Marcar como error
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
    """
    Maneja el comando /ytdl para descargar videos de YouTube
    """
    try:
        parts = text.strip().split()
        
        if len(parts) < 2:
            await message.reply("❗ Debes proporcionar una URL de YouTube después del comando.")
            return
        
        url = parts[1].strip()
        
        # Verificar si es una URL válida de YouTube
        if "youtube.com" not in url and "youtu.be" not in url:
            await message.reply("❗ URL no válida. Debe ser un enlace de YouTube.")
            return
        
        # Determinar si es solo audio basado en el parámetro -a
        audio_only = False
        if len(parts) > 2 and parts[2].strip() == "-a":
            audio_only = True
        
        chat_id = message.chat.id
        status_msg = await message.reply("⏳ Iniciando descarga de YouTube...")
        
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
            """Actualiza el mensaje de progreso de la descarga"""
            while progress_data["percent"] < 100 and progress_data["active"]:
                try:
                    elapsed = int(time.time() - start_time)
                    formatted_time = format_time(elapsed)
                    speed_mb = progress_data["speed"] / (1024 * 1024) if progress_data["speed"] > 0 else 0
                    
                    bar_length = 20
                    filled_length = int(bar_length * progress_data["percent"] / 100)
                    bar = "█" * filled_length + "▒" * (bar_length - filled_length)
                    
                    downloaded_mb = progress_data["downloaded"] / (1024 * 1024)
                    total_mb = progress_data["total_size"] / (1024 * 1024) if progress_data["total_size"] > 0 else 0
                    
                    status_text = (
                        f"📥 **Descargando de YouTube:**\n"
                        f"📄 **Archivo:** `{progress_data['filename']}`\n"
                        f"📊 **Progreso:** {progress_data['percent']:.1f}%\n"
                        f"📉 [{bar}]\n"
                        f"📦 **Descargado:** {format_size(progress_data['downloaded'])} / {format_size(progress_data['total_size'])}\n"
                        f"🚀 **Velocidad:** {speed_mb:.2f} MB/s\n"
                        f"⏱️ **Tiempo:** {formatted_time}\n"
                        f"🔊 **Modo:** {'Solo audio' if audio_only else 'Video completo'}"
                    )
                    
                    await safe_call(status_msg.edit_text, status_text)
                except Exception as e:
                    log(f"Error en update_progress: {e}")
                    break
                    
                await asyncio.sleep(5)
        
        # Iniciar tarea de actualización de progreso
        progress_task = asyncio.create_task(update_progress())
        
        try:
            # Realizar la descarga
            downloaded_file = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: download_youtube_video(url, download_id, progress_data, audio_only)
            )
            
            progress_data["active"] = False
            progress_data["state"] = "completed"
            
            # Esperar a que la tarea de progreso termine
            await asyncio.sleep(2)
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                await safe_call(status_msg.edit_text, "❌ Error: No se pudo descargar el archivo.")
                return
            
            # Preparar para enviar el archivo
            file_size = os.path.getsize(downloaded_file)
            file_size_mb = file_size / (1024 * 1024)
            filename = os.path.basename(downloaded_file)
            
            await safe_call(status_msg.edit_text, f"📤 Preparando envío: {filename} ({file_size_mb:.2f} MB)")
            
            # Función de progreso para la subida
            current_uploaded = 0
            
            def upload_progress(current, total):
                nonlocal current_uploaded
                current_uploaded = current
            
            # Enviar el archivo
            await safe_call(client.send_chat_action, chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
            
            if audio_only:
                await safe_call(client.send_audio, 
                               chat_id=chat_id, 
                               audio=downloaded_file, 
                               progress=upload_progress,
                               caption=f"🎵 {filename}")
            else:
                await safe_call(client.send_video, 
                               chat_id=chat_id, 
                               video=downloaded_file, 
                               progress=upload_progress,
                               caption=f"🎥 {filename}")
            
            # Limpiar archivo temporal
            try:
                os.remove(downloaded_file)
            except:
                pass
            
            await safe_call(status_msg.edit_text, "✅ Descarga y envío completados correctamente.")
            await asyncio.sleep(5)
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
